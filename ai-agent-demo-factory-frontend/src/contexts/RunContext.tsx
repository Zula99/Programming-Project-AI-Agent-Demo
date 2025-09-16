'use client'

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface CrawlRun {
    run_id: string;
    url: string;
    status: string;
    progress: number;
    started_at: number;
    completed_at?: number;
    template: string;
    pages_crawled: number;
    stats?: any;
}

interface RunContextType {
    selectedRunId: string | null;
    selectedRun: CrawlRun | null;
    setSelectedRun: (run: CrawlRun | null) => void;
    allRuns: CrawlRun[];
    setAllRuns: (runs: CrawlRun[]) => void;
}

const RunContext = createContext<RunContextType | undefined>(undefined);

export function RunProvider({ children }: { children: ReactNode }) {
    const [selectedRun, setSelectedRunState] = useState<CrawlRun | null>(null);
    const [allRuns, setAllRuns] = useState<CrawlRun[]>([]);

    const setSelectedRun = (run: CrawlRun | null) => {
        console.log('RunContext - setSelectedRun called with:', run);
        setSelectedRunState(run);
    };

    return (
        <RunContext.Provider value={{
            selectedRunId: selectedRun?.run_id || null,
            selectedRun,
            setSelectedRun,
            allRuns,
            setAllRuns
        }}>
            {children}
        </RunContext.Provider>
    );
}

export function useRunContext() {
    const context = useContext(RunContext);
    if (context === undefined) {
        throw new Error('useRunContext must be used within a RunProvider');
    }
    return context;
}