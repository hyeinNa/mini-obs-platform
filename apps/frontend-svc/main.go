package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
)

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
	defer cancel()

	// OTel init
	shutdown, err := setupOTel(ctx)
	if err != nil {
		slog.Error("failed to initialise OTel", slog.String("error", err.Error()))
		os.Exit(1)
	}
	defer func() {
		shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer shutdownCancel()
		if err := shutdown(shutdownCtx); err != nil {
			slog.Error("OTel shutdown error", slog.String("error", err.Error()))
		}
	}()

	orderSvcURL := envOrDefault("ORDER_SVC_URL", "http://localhost:8081")
	inventorySvcURL := envOrDefault("INVENTORY_SVC_URL", "http://localhost:8082")

	// Strip any trailing slashes from upstream URLs
	orderSvcURL = strings.TrimRight(orderSvcURL, "/")
	inventorySvcURL = strings.TrimRight(inventorySvcURL, "/")

	mux := http.NewServeMux()
	mux.Handle("/api/order", otelhttp.NewHandler(handleAPIOrder(orderSvcURL), "/api/order"))
	mux.Handle("/api/inventory", otelhttp.NewHandler(handleAPIInventory(inventorySvcURL), "/api/inventory"))
	mux.Handle("/metrics", promhttp.Handler())
	mux.HandleFunc("/health", handleHealth)

	port := envOrDefault("PORT", "8080")
	server := &http.Server{
		Addr:         ":" + port,
		Handler:      mux,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 30 * time.Second,
	}

	slog.Info("starting frontend-svc",
		slog.String("port", port),
		slog.String("order_svc_url", orderSvcURL),
		slog.String("inventory_svc_url", inventorySvcURL),
	)

	go func() {
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			slog.Error("server error", slog.String("error", err.Error()))
			os.Exit(1)
		}
	}()

	<-ctx.Done()
	slog.Info("shutdown signal received")

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()
	if err := server.Shutdown(shutdownCtx); err != nil {
		slog.Error("HTTP server shutdown error", slog.String("error", err.Error()))
	}
}

// stringBody converts a string payload to an io.Reader.
func stringBody(s string) *strings.Reader {
	return strings.NewReader(s)
}
