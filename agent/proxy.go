package main

import (
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
)

func (agent *DriftAgent) GetProxyForSession(sessionId string) (*httputil.ReverseProxy, error) {
	// split host to get session id
	sessionId = strings.Split(sessionId, ".")[0]

	agent.Mutex.RLock()
	backend, ok := agent.Sessions[sessionId]
	agent.Mutex.RUnlock()
	if !ok {
		return nil, http.ErrServerClosed
	}

	target, err := url.Parse(fmt.Sprintf("http://127.0.0.1:%d", backend.LocalDebuggingPort))
	if err != nil {
		return nil, err
	}
	proxy := httputil.NewSingleHostReverseProxy(target)

	// Fix director so backend only sees `/json/...`
	originalDirector := proxy.Director
	proxy.Director = func(req *http.Request) {
		originalDirector(req)

		// strip "/<sessionId>" prefix from path before forwarding
		parts := strings.SplitN(req.URL.Path, "/", 3)
		if len(parts) >= 3 {
			req.URL.Path = "/" + parts[2]
		} else {
			req.URL.Path = "/"
		}
		req.Host = target.Host
	}

	// Modify /json responses
	proxy.ModifyResponse = func(resp *http.Response) error {
		if strings.HasPrefix(resp.Request.URL.Path, "/json") {
			body, err := io.ReadAll(resp.Body)
			if err != nil {
				return err
			}
			_ = resp.Body.Close()

			// Replace "127.0.0.1:port" with public hostname + sessionId path
			replaced := strings.ReplaceAll(string(body), target.Host, fmt.Sprintf("%s:%d/%s", agent.Domain, agent.BrowserProxyPort(), sessionId))

			// Check if we need to replace ws:// with wss://
			if agent.IsHttps {
				replaced = strings.ReplaceAll(replaced, "ws://", "wss://")
			}

			resp.Body = io.NopCloser(strings.NewReader(replaced))
			resp.ContentLength = int64(len(replaced))
			resp.Header.Set("Content-Length", fmt.Sprint(len(replaced)))
		}
		return nil
	}

	return proxy, nil
}

func (agent *DriftAgent) ProxyHandler(w http.ResponseWriter, r *http.Request) {
	// Expect path like /<sessionId>/json/version
	parts := strings.SplitN(strings.TrimPrefix(r.URL.Path, "/"), "/", 2)
	if len(parts) < 1 {
		http.Error(w, "invalid path", http.StatusBadRequest)
		return
	}
	sessionId := parts[0]

	agent.Mutex.RLock()
	expectedToken, ok := agent.Sessions[sessionId]
	agent.Mutex.RUnlock()

	if !ok {
		http.Error(w, "unknown host", http.StatusBadGateway)
		return
	}

	// Try Basic Auth first
	if username, password, ok := r.BasicAuth(); ok {
		if username == "cdp" && password == expectedToken.AuthToken {
			// valid -> continue
			goto AUTH_OK
		}
	}

	// Try Bearer token
	if auth := r.Header.Get("Authorization"); strings.HasPrefix(auth, "Bearer ") {
		if strings.TrimPrefix(auth, "Bearer ") == expectedToken.AuthToken {
			// valid -> continue
			goto AUTH_OK
		}
	}

	// Neither matched
	w.Header().Set("WWW-Authenticate", `Basic realm="CDP"`)
	http.Error(w, "unauthorized", http.StatusUnauthorized)
	return

AUTH_OK:

	// Proxy request
	proxy, err := agent.GetProxyForSession(sessionId)
	if err != nil {
		http.Error(w, "backend error", http.StatusInternalServerError)
		return
	}

	log.Printf("[proxy] session=%s path=%s", sessionId, r.URL.Path)
	proxy.ServeHTTP(w, r)
}

func (agent *DriftAgent) StartBrowserProxy() {
	agent.browserProxyServer = &http.Server{
		Addr:      fmt.Sprintf(":%d", agent.BrowserProxyPort()),
		Handler:   http.HandlerFunc(agent.ProxyHandler),
		TLSConfig: agent.tlsConfig,
	}
	go func() {
		fmt.Printf("Starting browser proxy on port %d\n", agent.BrowserProxyPort())
		var err error
		if agent.IsHttps {
			err = agent.browserProxyServer.ListenAndServeTLS("", "")
		} else {
			err = agent.browserProxyServer.ListenAndServe()
		}
		if err != nil {
			fmt.Printf("browser proxy server stopped: %v\n", err)
		}
	}()
}

func (agent *DriftAgent) StopBrowserProxy() {
	if agent.browserProxyServer == nil {
		return
	}
	_ = agent.browserProxyServer.Close()
}
