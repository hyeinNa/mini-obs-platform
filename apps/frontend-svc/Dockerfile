# syntax=docker/dockerfile:1
# ---- build stage ----
FROM golang:1.24-alpine AS builder

RUN apk add --no-cache ca-certificates

WORKDIR /app

# Copy module files and source
COPY go.mod *.go ./
RUN go mod tidy && CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o frontend-svc .

# ---- runtime stage ----
FROM scratch AS runtime

COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /app/frontend-svc /frontend-svc

ENV OTEL_SERVICE_NAME=frontend-svc
ENV ORDER_SVC_URL=http://order-svc:8081
ENV INVENTORY_SVC_URL=http://inventory-svc:8082
ENV OTEL_EXPORTER_OTLP_ENDPOINT=otel-collector:4317

EXPOSE 8080

ENTRYPOINT ["/frontend-svc"]
