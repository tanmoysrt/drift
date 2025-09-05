package main

import (
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/labstack/echo/v4"
)

func (agent *DriftAgent) StartAPIServer() {
	// Initialize Echo instance
	agent.echoHandler = echo.New()
	agent.echoHandler.HideBanner = true
	agent.echoHandler.HidePort = true

	// Middleware for Authentication
	agent.echoHandler.Use(func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			authHeader := c.Request().Header.Get("Authorization")
			if authHeader == "" {
				return c.JSON(http.StatusUnauthorized, map[string]string{
					"error": "missing Authorization header",
				})
			}
			if !strings.HasPrefix(authHeader, "Bearer ") {
				return c.JSON(http.StatusUnauthorized, map[string]string{
					"error": "invalid Authorization format",
				})
			}
			token := strings.TrimPrefix(authHeader, "Bearer ")
			if token == "" {
				return c.JSON(http.StatusUnauthorized, map[string]string{
					"error": "empty token",
				})
			}
			if token != agent.AuthToken {
				return c.JSON(http.StatusUnauthorized, map[string]string{
					"error": "invalid token",
				})
			}
			return next(c)
		}
	})

	// Register API routes
	agent.registerAPIRoutes()

	// Start the server
	go func() {
		port := 80
		if agent.IsHttps {
			port = 443
		}
		address := fmt.Sprintf(":%d", port)
		fmt.Printf("Starting API server on port %d\n", port)
		if agent.IsHttps {
			agent.apiServer = &http.Server{
				Addr:      address,
				Handler:   agent.echoHandler,
				TLSConfig: agent.tlsConfig,
			}
			if err := agent.apiServer.ListenAndServeTLS("", ""); err != nil {
				fmt.Printf("api tls server stopped: %v\n", err)
			}
		} else {
			agent.apiServer = &http.Server{
				Addr:    address,
				Handler: agent.echoHandler,
			}
			if err := agent.apiServer.ListenAndServe(); err != nil {
				fmt.Printf("api server stopped: %v\n", err)
			}
		}
	}()
}

func (agent *DriftAgent) StopAPIServer() error {
	if agent.echoHandler != nil {
		return agent.echoHandler.Close()
	}
	return nil
}

// API Routes
func (agent *DriftAgent) registerAPIRoutes() {
	agent.echoHandler.GET("/health", agent.HealthCheckAPI)
	agent.echoHandler.GET("/sessions", agent.GetBrowserSessionsAPI)
	agent.echoHandler.POST("/sessions", agent.CreateBrowserSessionAPI)
	agent.echoHandler.GET("/sessions/:session_id", agent.GetBrowserSessionAPI)
	agent.echoHandler.DELETE("/sessions/:session_id", agent.TerminateBrowserSessionAPI)
	agent.echoHandler.GET("/sessions/:session_id/active", agent.IsBrowserSessionActiveAPI)
	agent.echoHandler.GET("/sessions/:session_id/videos", agent.FetchBrowserSessionVideosAPI)
	agent.echoHandler.DELETE("/sessions/:session_id/videos", agent.DeleteSessionVideosAPI)
	agent.echoHandler.GET("/sessions/:session_id/videos/:video_id", agent.GetVideoSessionAPI)
}

func (agent *DriftAgent) HealthCheckAPI(ctx echo.Context) error {
	return ctx.JSON(200, map[string]any{"status": "ok", "sessions": len(agent.Sessions)})
}

func (agent *DriftAgent) GetBrowserSessionsAPI(ctx echo.Context) error {
	session_ids := make([]map[string]any, 0)
	agent.Mutex.RLock()
	defer agent.Mutex.RUnlock()
	for sessionId, session := range agent.Sessions {
		session_ids = append(session_ids, map[string]any{
			"session_id": sessionId,
			"created_on": session.CreatedOn,
			"videos":     agent.GetSessionVideos(sessionId),
		})
	}
	return ctx.JSON(200, session_ids)
}

func (agent *DriftAgent) CreateBrowserSessionAPI(ctx echo.Context) error {
	session, err := agent.CreateBrowserSession()
	if err != nil {
		return ctx.JSON(500, map[string]string{"error": err.Error()})
	}
	return ctx.JSON(200, map[string]any{
		"session_id": session.Id,
		"created_on": session.CreatedOn,
		"auth_token": session.AuthToken,
		"endpoint":   agent.GenerateBrowserSessionEndpoint(session.Id),
	})
}

func (agent *DriftAgent) GetBrowserSessionAPI(ctx echo.Context) error {
	sessionId := ctx.Param("session_id")
	agent.Mutex.RLock()
	session, ok := agent.Sessions[sessionId]
	agent.Mutex.RUnlock()

	if !ok {
		return ctx.JSON(404, map[string]string{"error": "session not found"})
	}

	videos := agent.GetSessionVideos(sessionId)

	return ctx.JSON(200, map[string]any{
		"session_id": session.Id,
		"created_on": session.CreatedOn,
		"videos":     videos,
	})
}

func (agent *DriftAgent) IsBrowserSessionActiveAPI(ctx echo.Context) error {
	sessionId := ctx.Param("session_id")
	active := agent.IsBrowserSessionActive(sessionId)
	return ctx.JSON(200, map[string]bool{"active": active})
}

func (agent *DriftAgent) TerminateBrowserSessionAPI(ctx echo.Context) error {
	sessionId := ctx.Param("session_id")
	err := agent.TerminateBrowserSession(sessionId)
	if err != nil {
		return ctx.JSON(500, map[string]string{"error": err.Error()})
	}
	return ctx.JSON(200, map[string]string{"status": "terminated"})
}

func (agent *DriftAgent) FetchBrowserSessionVideosAPI(ctx echo.Context) error {
	sessionId := ctx.Param("session_id")
	videos := agent.GetSessionVideos(sessionId)
	return ctx.JSON(200, videos)
}

func (agent *DriftAgent) DeleteSessionVideosAPI(ctx echo.Context) error {
	sessionId := ctx.Param("session_id")
	err := agent.DeleteSessionVideos(sessionId)
	if err != nil {
		return ctx.JSON(500, map[string]string{"error": err.Error()})
	}
	return ctx.JSON(200, map[string]string{"status": "deleted"})
}

func (agent *DriftAgent) GetVideoSessionAPI(ctx echo.Context) error {
	sessionId := ctx.Param("session_id")
	videoId := ctx.Param("video_id")

	// Sanitize session ID and video ID to prevent directory traversal attacks
	sessionId = filepath.Clean(sessionId)
	videoId = filepath.Clean(videoId)

	videoPath := filepath.Join(agent.RecordingDirectory, sessionId, videoId)
	videoPath = filepath.Clean(videoPath)

	// Check if the file exists
	if _, err := os.Stat(videoPath); os.IsNotExist(err) {
		return ctx.JSON(404, "video not found")
	}

	return ctx.Inline(videoPath, videoId)
}
