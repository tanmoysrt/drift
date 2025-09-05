package main

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/labstack/gommon/random"
	"github.com/playwright-community/playwright-go"
)

type BrowserSession struct {
	Id                 string
	AuthToken          string
	LocalDebuggingPort uint16
	Playwright         *playwright.Playwright
	Browser            playwright.BrowserContext
	CreatedOn          int64
	WaitCh             chan struct{}

	cleanupMutex   sync.Mutex
	cleanupStarted bool
}

var USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

func (agent *DriftAgent) CreateBrowserSession() (*BrowserSession, error) {
	sessionId := strings.ReplaceAll(uuid.New().String(), "-", "")
	availablePort, err := findAvailablePort()
	if err != nil {
		return nil, err
	}

	// Create user data directory if not exists
	err = os.MkdirAll(filepath.Join(agent.UserDataDirectory, sessionId), os.ModePerm)
	if err != nil {
		return nil, fmt.Errorf("could not create user data directory: %w", err)
	}

	// Create recording directory if not exists
	err = os.MkdirAll(filepath.Join(agent.RecordingDirectory, sessionId), os.ModePerm)
	if err != nil {
		return nil, fmt.Errorf("could not create recording directory: %w", err)
	}

	// Create playwright instance
	pw, err := playwright.Run()
	if err != nil {
		return nil, fmt.Errorf("could not launch playwright: %w", err)
	}

	// Create browser context
	browser, err := pw.Chromium.LaunchPersistentContext(filepath.Join(agent.UserDataDirectory, sessionId), playwright.BrowserTypeLaunchPersistentContextOptions{
		Headless: playwright.Bool(agent.Headless),
		Args: []string{
			fmt.Sprintf("--remote-debugging-port=%d", availablePort),
			"--remote-debugging-address=127.0.0.1",
			"--disable-blink-features=AutomationControlled",
			"--disable-dev-shm-usage",
			"--no-first-run",
			"--no-default-browser-check",
		},
		Viewport: &playwright.Size{
			Width:  1920,
			Height: 1080,
		},
		RecordVideo: &playwright.RecordVideo{
			Dir:  filepath.Join(agent.RecordingDirectory, sessionId),
			Size: &playwright.Size{Width: 1920, Height: 1080},
		},
		UserAgent: &USER_AGENT,
	})
	if err != nil {
		pw.Stop()
		if browser != nil {
			browser.Close()
		}
		return nil, fmt.Errorf("could not launch browser: %w", err)
	}

	browser.OnClose(func(context playwright.BrowserContext) {
		err := agent.TerminateBrowserSession(sessionId)
		if err != nil {
			fmt.Printf("error terminating browser session %s: %v\n", sessionId, err)
		}
	})

	session := &BrowserSession{
		Id:                 sessionId,
		LocalDebuggingPort: availablePort,
		AuthToken:          random.String(64),
		CreatedOn:          time.Now().Unix(),
		Playwright:         pw,
		Browser:            browser,
		WaitCh:             make(chan struct{}),
		cleanupMutex:       sync.Mutex{},
		cleanupStarted:     false,
	}

	agent.Mutex.Lock()
	agent.Sessions[sessionId] = session
	agent.Mutex.Unlock()

	return session, nil
}

func (agent *DriftAgent) TerminateBrowserSession(sessionId string) error {
	agent.Mutex.RLock()
	session, ok := agent.Sessions[sessionId]
	agent.Mutex.RUnlock()

	if !ok {
		return nil
	}

	session.cleanupMutex.Lock()
	if session.cleanupStarted {
		session.cleanupMutex.Unlock()
		// Cleanup already started
		return nil
	}

	session.cleanupStarted = true
	session.cleanupMutex.Unlock()

	go func() {

		// Send termination signal
		close(session.WaitCh)

		// Remove session from map
		agent.Mutex.Lock()
		delete(agent.Sessions, sessionId)
		agent.Mutex.Unlock()

		if session.Browser != nil {
			// Close the pages
			if session.Browser.Pages() != nil {
				for _, page := range session.Browser.Pages() {
					_ = page.Close()
				}
			}
			// Close the browser
			session.Browser.Close()
		}

		if session.Playwright != nil {
			// Stop the playwright instance
			session.Playwright.Stop()
		}

		_ = os.RemoveAll(filepath.Join(agent.UserDataDirectory, sessionId))
	}()
	return nil
}

func (agent *DriftAgent) TerminateAllBrowserSessions() {
	agent.Mutex.RLock()
	var sessionIds []string
	for sessionId := range agent.Sessions {
		sessionIds = append(sessionIds, sessionId)
	}
	agent.Mutex.RUnlock()

	for _, sessionId := range sessionIds {
		err := agent.TerminateBrowserSession(sessionId)
		if err != nil {
			fmt.Printf("error terminating browser session %s: %v\n", sessionId, err)
		}
	}
}

func (agent *DriftAgent) IsBrowserSessionActive(sessionId string) bool {
	agent.Mutex.RLock()
	session, ok := agent.Sessions[sessionId]
	agent.Mutex.RUnlock()

	if !ok {
		return false
	}

	// Check if we can still access the browser
	if session.Browser == nil {
		return false
	}

	// Check if any pages are open
	pages := session.Browser.Pages()
	if len(pages) == 0 {
		agent.TerminateBrowserSession(sessionId)
		return false
	}

	return true
}

func (agent *DriftAgent) WaitForBrowserSessionTermination(sessionId string) {
	agent.Mutex.RLock()
	session, ok := agent.Sessions[sessionId]
	agent.Mutex.RUnlock()
	if !ok {
		return
	}

	<-session.WaitCh
}

func (agent *DriftAgent) CleanupUserDataDirectories() {
	entries, err := os.ReadDir(agent.UserDataDirectory)
	if err != nil {
		return
	}

	for _, entry := range entries {
		if entry.IsDir() {
			err := os.RemoveAll(filepath.Join(agent.UserDataDirectory, entry.Name()))
			if err != nil {
				fmt.Printf("could not remove user data directory %s: %v\n", entry.Name(), err)
			}
		}
	}
}

type videoEntry struct {
	name    string
	modTime int64
}

func (agent *DriftAgent) GetSessionVideos(sessionId string) []string {
	videoDir := filepath.Join(agent.RecordingDirectory, sessionId)
	// Check if directory exists
	if _, err := os.Stat(videoDir); os.IsNotExist(err) {
		return []string{}
	}
	// Read directory contents .webm files only
	entries, err := os.ReadDir(videoDir)
	if err != nil {
		return []string{}
	}

	var videoEntries []videoEntry

	for _, entry := range entries {
		if entry.Type().IsRegular() && strings.HasSuffix(entry.Name(), ".webm") {
			info, err := entry.Info()
			if err != nil {
				continue
			}
			videoEntries = append(videoEntries, videoEntry{
				name:    entry.Name(),
				modTime: info.ModTime().Unix(),
			})
		}
	}

	// Sort by creation/modification time (oldest first)
	sort.Slice(videoEntries, func(i, j int) bool {
		return videoEntries[i].modTime < videoEntries[j].modTime
	})

	var videos []string
	for _, ve := range videoEntries {
		videos = append(videos, ve.name)
	}

	return videos
}

func (agent *DriftAgent) DeleteSessionVideos(sessionId string) error {
	videoDir := filepath.Join(agent.RecordingDirectory, sessionId)
	// Check if directory exists
	if _, err := os.Stat(videoDir); os.IsNotExist(err) {
		return nil
	}
	// Read directory contents .webm files only
	entries, err := os.ReadDir(videoDir)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		if entry.Type().IsRegular() && strings.HasSuffix(entry.Name(), ".webm") {
			err := os.Remove(filepath.Join(videoDir, entry.Name()))
			if err != nil {
				fmt.Printf("could not remove video file %s: %v\n", entry.Name(), err)
			}
		}
	}

	return nil
}
