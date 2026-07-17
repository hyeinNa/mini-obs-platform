package main

import (
	"context"
	"fmt"
	"os"
	"strings"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

// setupOTel initialises the global TracerProvider with an OTLP gRPC exporter
// and W3C TraceContext propagation. It returns a shutdown function that must be
// deferred by the caller.
func setupOTel(ctx context.Context) (func(context.Context) error, error) {
	serviceName := envOrDefault("OTEL_SERVICE_NAME", "frontend-svc")
	otlpEndpoint := envOrDefault("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
	// gRPC NewClient expects host:port without scheme
	otlpEndpoint = strings.TrimPrefix(otlpEndpoint, "http://")
	otlpEndpoint = strings.TrimPrefix(otlpEndpoint, "https://")

	conn, err := grpc.NewClient(
		otlpEndpoint,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		return nil, fmt.Errorf("otel: grpc dial %s: %w", otlpEndpoint, err)
	}

	exporter, err := otlptracegrpc.New(ctx, otlptracegrpc.WithGRPCConn(conn))
	if err != nil {
		return nil, fmt.Errorf("otel: create exporter: %w", err)
	}

	res, err := resource.New(ctx,
		resource.WithAttributes(semconv.ServiceName(serviceName)),
	)
	if err != nil {
		return nil, fmt.Errorf("otel: create resource: %w", err)
	}

	provider := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
	)
	otel.SetTracerProvider(provider)
	otel.SetTextMapPropagator(propagation.TraceContext{})

	shutdown := func(ctx context.Context) error {
		return provider.Shutdown(ctx)
	}
	return shutdown, nil
}

func envOrDefault(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
