import { useState, useCallback } from 'react';

export type RunStatus = "idle" | "running" | "complete" | "error";

export interface CrawlRun {
    id: string;
    url: string;
    status: RunStatus;
    startedAt: string;
    completedAt?: string;
    pages: number;
    error?: string;
}

export interface CrawlerState {
    currentRun: CrawlRun | null;
    recentRuns: CrawlRun[];
    isStarting: boolean;
}

export const useCrawler = () => {
    const [state, setState] = useState<CrawlerState>({
        currentRun: null,
        recentRuns: [
            { 
                id: "RUN-001", 
                url: "https://example.com", 
                status: "complete", 
                startedAt: "14 Aug, 2025 09:00am",
                completedAt: "14 Aug, 2025 09:15am",
                pages: 42 
            },
            { 
                id: "RUN-002", 
                url: "https://nab.com.au", 
                status: "complete", 
                startedAt: "14 Aug, 2025 08:00am",
                completedAt: "14 Aug, 2025 08:45am",
                pages: 1002 
            },
            { 
                id: "RUN-003", 
                url: "https://agilent.com", 
                status: "running", 
                startedAt: "14 Aug, 2025 10:12am",
                pages: 5 
            }
        ],
        isStarting: false
    });

    // URL validation function
    const validateURL = useCallback((url: string): { isValid: boolean; error?: string } => {
        if (!url.trim()) {
            return { isValid: false, error: "Please enter a URL" };
        }

        try {
            const urlObj = new URL(url);
            if (!['http:', 'https:'].includes(urlObj.protocol)) {
                return { isValid: false, error: "Only HTTP and HTTPS protocols are supported" };
            }
            return { isValid: true };
        } catch {
            return { isValid: false, error: "Please enter a valid URL format" };
        }
    }, []);

    // Generate run ID
    const generateRunId = useCallback((): string => {
        const timestamp = Date.now();
        const random = Math.floor(Math.random() * 1000);
        return `RUN-${timestamp}-${random}`;
    }, []);

    // Start crawler task
    const startCrawl = useCallback(async (url: string): Promise<{ success: boolean; error?: string }> => {
        const validation = validateURL(url);
        if (!validation.isValid) {
            return { success: false, error: validation.error };
        }

        setState(prev => ({ ...prev, isStarting: true }));

        try {
            // Simulate API call delay
            await new Promise(resolve => setTimeout(resolve, 1000));

            const newRun: CrawlRun = {
                id: generateRunId(),
                url: url.trim(),
                status: "running",
                startedAt: new Date().toLocaleString('en-US', {
                    day: 'numeric',
                    month: 'short',
                    year: 'numeric',
                    hour: 'numeric',
                    minute: 'numeric',
                    hour12: true
                }),
                pages: 0
            };

            // Update state
            setState(prev => ({
                ...prev,
                currentRun: newRun,
                recentRuns: [newRun, ...prev.recentRuns.slice(0, 9)], // Keep last 10
                isStarting: false
            }));

            // Simulate crawler progress update
            setTimeout(() => {
                setState(prev => {
                    if (prev.currentRun && prev.currentRun.id === newRun.id) {
                        return {
                            ...prev,
                            currentRun: { ...prev.currentRun, pages: 5 }
                        };
                    }
                    return prev;
                });
            }, 2000);

            // Simulate crawler completion
            setTimeout(() => {
                setState(prev => {
                    if (prev.currentRun && prev.currentRun.id === newRun.id) {
                        const completedRun = { 
                            ...prev.currentRun, 
                            status: "complete" as RunStatus,
                            completedAt: new Date().toLocaleString('en-US', {
                                day: 'numeric',
                                month: 'short',
                                year: 'numeric',
                                hour: 'numeric',
                                minute: 'numeric',
                                hour12: true
                            }),
                            pages: 25
                        };
                        
                        return {
                            ...prev,
                            currentRun: null,
                            recentRuns: prev.recentRuns.map(run => 
                                run.id === newRun.id ? completedRun : run
                            )
                        };
                    }
                    return prev;
                });
            }, 10000);

            return { success: true };
        } catch (error) {
            setState(prev => ({ ...prev, isStarting: false }));
            return { success: false, error: "Failed to start crawler, please try again" };
        }
    }, [validateURL, generateRunId]);

    // Stop current crawler task
    const stopCrawl = useCallback(async (): Promise<{ success: boolean; error?: string }> => {
        if (!state.currentRun) {
            return { success: false, error: "No running task to stop" };
        }

        try {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 500));

            setState(prev => {
                if (prev.currentRun) {
                    const stoppedRun = { 
                        ...prev.currentRun, 
                        status: "complete" as RunStatus,
                        completedAt: new Date().toLocaleString('en-US', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                            hour: 'numeric',
                            minute: 'numeric',
                            hour12: true
                        })
                    };
                    
                    return {
                        ...prev,
                        currentRun: null,
                        recentRuns: prev.recentRuns.map(run => 
                            run.id === prev.currentRun!.id ? stoppedRun : run
                        )
                    };
                }
                return prev;
            });

            return { success: true };
        } catch (error) {
            return { success: false, error: "Failed to stop crawler, please try again" };
        }
    }, [state.currentRun]);

    return {
        ...state,
        startCrawl,
        stopCrawl,
        validateURL
    };
};
