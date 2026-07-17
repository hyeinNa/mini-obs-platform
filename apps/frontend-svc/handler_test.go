package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// ---------------------------------------------------------------------------
// Unit tests — pure logic
// ---------------------------------------------------------------------------

func TestEnvOrDefault_returnsEnvWhenSet(t *testing.T) {
	t.Setenv("TEST_KEY", "custom-value")
	got := envOrDefault("TEST_KEY", "fallback")
	if got != "custom-value" {
		t.Errorf("envOrDefault = %q, want %q", got, "custom-value")
	}
}

func TestEnvOrDefault_returnsFallbackWhenUnset(t *testing.T) {
	got := envOrDefault("TEST_KEY_UNSET_XYZ", "fallback")
	if got != "fallback" {
		t.Errorf("envOrDefault = %q, want %q", got, "fallback")
	}
}

// ---------------------------------------------------------------------------
// Integration tests — handlers called via httptest.NewRecorder
// ---------------------------------------------------------------------------

func TestHandleHealth_returnsOK(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()

	handleHealth(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", w.Code, http.StatusOK)
	}

	var body map[string]any
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("response is not valid JSON: %v", err)
	}
	if body["status"] != "ok" {
		t.Errorf("status field = %v, want %q", body["status"], "ok")
	}
	if body["service"] != "frontend-svc" {
		t.Errorf("service field = %v, want %q", body["service"], "frontend-svc")
	}
}

func TestHandleAPIOrder_upstreamSuccess(t *testing.T) {
	// Fake order-svc that returns a successful 201 response
	fakeOrderSvc := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost || r.URL.Path != "/orders" {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		_, _ = w.Write([]byte(`{"order_id":"ord-test","item_id":"item-001","quantity":1,"status":"created"}`))
	}))
	defer fakeOrderSvc.Close()

	handler := handleAPIOrder(fakeOrderSvc.URL)
	req := httptest.NewRequest(http.MethodGet, "/api/order", nil)
	w := httptest.NewRecorder()
	handler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", w.Code, http.StatusOK)
	}

	var body map[string]any
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("response is not valid JSON: %v", err)
	}
	if body["order_id"] != "ord-test" {
		t.Errorf("order_id = %v, want %q", body["order_id"], "ord-test")
	}
}

func TestHandleAPIOrder_upstreamDown_returns502(t *testing.T) {
	// Point to a port that is not listening
	handler := handleAPIOrder("http://localhost:19999")
	req := httptest.NewRequest(http.MethodGet, "/api/order", nil)
	w := httptest.NewRecorder()
	handler(w, req)

	if w.Code != http.StatusBadGateway {
		t.Errorf("status = %d, want %d", w.Code, http.StatusBadGateway)
	}
}

func TestHandleAPIInventory_upstreamSuccess(t *testing.T) {
	fakeInventorySvc := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet || r.URL.Path != "/items" {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"items":[{"item_id":"item-001","name":"Widget A","stock":100}]}`))
	}))
	defer fakeInventorySvc.Close()

	handler := handleAPIInventory(fakeInventorySvc.URL)
	req := httptest.NewRequest(http.MethodGet, "/api/inventory", nil)
	w := httptest.NewRecorder()
	handler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", w.Code, http.StatusOK)
	}

	var body map[string]any
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("response is not valid JSON: %v", err)
	}
	if _, ok := body["items"]; !ok {
		t.Error("response missing 'items' field")
	}
}

func TestHandleAPIInventory_upstreamDown_returns502(t *testing.T) {
	handler := handleAPIInventory("http://localhost:19998")
	req := httptest.NewRequest(http.MethodGet, "/api/inventory", nil)
	w := httptest.NewRecorder()
	handler(w, req)

	if w.Code != http.StatusBadGateway {
		t.Errorf("status = %d, want %d", w.Code, http.StatusBadGateway)
	}
}

func TestHandleAPIOrder_upstreamConflict_returns409(t *testing.T) {
	fakeOrderSvc := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusConflict)
		_, _ = w.Write([]byte(`{"detail":"insufficient stock"}`))
	}))
	defer fakeOrderSvc.Close()

	handler := handleAPIOrder(fakeOrderSvc.URL)
	req := httptest.NewRequest(http.MethodGet, "/api/order", nil)
	w := httptest.NewRecorder()
	handler(w, req)

	if w.Code != http.StatusConflict {
		t.Errorf("status = %d, want %d", w.Code, http.StatusConflict)
	}
}
