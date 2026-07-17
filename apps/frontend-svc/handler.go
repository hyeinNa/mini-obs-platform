package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/trace"
)

// Prometheus metrics — registered once at package init.
var (
	httpRequestsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total HTTP requests",
		},
		[]string{"method", "path", "status_code", "service"},
	)
	httpRequestDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_request_duration_seconds",
			Help:    "HTTP request duration in seconds",
			Buckets: []float64{0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0},
		},
		[]string{"method", "path", "service"},
	)
)

func init() {
	prometheus.MustRegister(httpRequestsTotal, httpRequestDuration)
}

// traceID extracts the current trace ID from ctx as a 32-hex string.
func traceID(ctx context.Context) string {
	span := trace.SpanFromContext(ctx)
	if !span.SpanContext().IsValid() {
		return ""
	}
	return span.SpanContext().TraceID().String()
}

// injectHeaders injects W3C TraceContext headers into an http.Header map.
func injectHeaders(ctx context.Context, h http.Header) {
	otel.GetTextMapPropagator().Inject(ctx, propagation.HeaderCarrier(h))
}

// extractContext extracts W3C TraceContext from incoming request headers.
func extractContext(r *http.Request) context.Context {
	return otel.GetTextMapPropagator().Extract(r.Context(), propagation.HeaderCarrier(r.Header))
}

// doUpstream performs an HTTP request to an upstream service, propagating
// TraceContext headers. It returns the decoded JSON body as a map.
func doUpstream(ctx context.Context, method, url string, body io.Reader) (map[string]any, int, error) {
	req, err := http.NewRequestWithContext(ctx, method, url, body)
	if err != nil {
		return nil, 0, fmt.Errorf("build request: %w", err)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	injectHeaders(ctx, req.Header)

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, 0, fmt.Errorf("upstream call: %w", err)
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, resp.StatusCode, fmt.Errorf("read body: %w", err)
	}

	var result map[string]any
	if err := json.Unmarshal(raw, &result); err != nil {
		return nil, resp.StatusCode, fmt.Errorf("decode JSON: %w", err)
	}
	return result, resp.StatusCode, nil
}

// handleAPIOrder proxies to order-svc POST /orders and returns the result.
func handleAPIOrder(orderSvcURL string) http.HandlerFunc {
	tracer := otel.Tracer("frontend-svc")

	return func(w http.ResponseWriter, r *http.Request) {
		ctx := extractContext(r)
		start := time.Now()

		ctx, span := tracer.Start(ctx, "GET /api/order",
			trace.WithSpanKind(trace.SpanKindServer),
		)
		defer span.End()

		slog.InfoContext(ctx, "handling GET /api/order",
			slog.String("trace_id", traceID(ctx)),
		)

		payload := `{"item_id":"item-001","quantity":1}`
		upstream := orderSvcURL + "/orders"
		result, statusCode, err := doUpstream(ctx, http.MethodPost, upstream, stringBody(payload))

		elapsed := time.Since(start).Seconds()
		httpRequestDuration.WithLabelValues("GET", "/api/order", "frontend-svc").Observe(elapsed)

		if err != nil || statusCode >= 500 {
			slog.ErrorContext(ctx, "order upstream failed",
				slog.String("error", fmt.Sprintf("%v", err)),
				slog.Int("status_code", statusCode),
				slog.String("upstream_url", upstream),
			)
			span.SetStatus(codes.Error, fmt.Sprintf("upstream error: %v", err))
			httpRequestsTotal.WithLabelValues("GET", "/api/order", "502", "frontend-svc").Inc()
			http.Error(w, `{"error":"upstream unavailable"}`, http.StatusBadGateway)
			return
		}
		if statusCode == http.StatusConflict {
			httpRequestsTotal.WithLabelValues("GET", "/api/order", "409", "frontend-svc").Inc()
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusConflict)
			_ = json.NewEncoder(w).Encode(result)
			return
		}

		result["trace_id"] = traceID(ctx)
		span.SetAttributes(attribute.String("order.trace_id", traceID(ctx)))

		httpRequestsTotal.WithLabelValues("GET", "/api/order", "200", "frontend-svc").Inc()
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(result)
	}
}

// handleAPIInventory proxies to inventory-svc GET /items.
func handleAPIInventory(inventorySvcURL string) http.HandlerFunc {
	tracer := otel.Tracer("frontend-svc")

	return func(w http.ResponseWriter, r *http.Request) {
		ctx := extractContext(r)
		start := time.Now()

		ctx, span := tracer.Start(ctx, "GET /api/inventory",
			trace.WithSpanKind(trace.SpanKindServer),
		)
		defer span.End()

		slog.InfoContext(ctx, "handling GET /api/inventory",
			slog.String("trace_id", traceID(ctx)),
		)

		upstream := inventorySvcURL + "/items"
		result, statusCode, err := doUpstream(ctx, http.MethodGet, upstream, nil)

		elapsed := time.Since(start).Seconds()
		httpRequestDuration.WithLabelValues("GET", "/api/inventory", "frontend-svc").Observe(elapsed)

		if err != nil || statusCode >= 500 {
			span.SetStatus(codes.Error, fmt.Sprintf("upstream error: %v", err))
			httpRequestsTotal.WithLabelValues("GET", "/api/inventory", "502", "frontend-svc").Inc()
			http.Error(w, `{"error":"upstream unavailable"}`, http.StatusBadGateway)
			return
		}

		result["trace_id"] = traceID(ctx)

		httpRequestsTotal.WithLabelValues("GET", "/api/inventory", "200", "frontend-svc").Inc()
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(result)
	}
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprint(w, `{"status":"ok","service":"frontend-svc"}`)
}
