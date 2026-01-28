
import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';
import { RunWizard } from './components/RunWizard';
import { ShotEditor } from './components/ShotEditor';
import { AppView, Run } from './types';
import { api } from './lib/api';

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<AppView>(AppView.DASHBOARD);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch runs from backend
  useEffect(() => {
    loadRuns();
  }, []);

  const loadRuns = async () => {
    try {
      setLoading(true);
      const backendRuns = await api.getRuns();

      // Transform backend data to GUI format
      const transformedRuns: Run[] = backendRuns.map(run => ({
        id: run.run_id,
        name: run.video_id || run.run_id, // Use video_id as name, fallback to run_id
        status: run.status?.stage_status === 'done' ? 'completed' :
          run.status?.stage_status === 'running' ? 'active' : 'draft',
        model: 'gemini-3-pro-preview', // Default for now
        visualStyle: 'Standard', // Default for now
        createdAt: run.created_at,
        shotsCount: 0, // Will be updated when viewing shot details
      }));

      setRuns(transformedRuns);
    } catch (error) {
      console.error('Failed to load runs:', error);
      // Fallback to empty array on error
      setRuns([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRun = async (newRun: Partial<Run>, files: { script: File; styleBible: File; voiceover: File } | null) => {
    const runId = `RUN-${Math.floor(Math.random() * 10000)}`;
    const videoId = `VID_${Math.floor(Math.random() * 1000)}`; // Simple random video ID

    try {
      if (files) {
        // Create run in backend
        await api.createRun(runId, videoId, files);

        // Trigger planning stage
        // Note: In a real app we might want to wait or show progress
        api.executeStage(runId, 'planning', videoId).catch(console.error);
      } else {
        console.warn("No files provided, creating local-only run state (backend sync may fail)");
      }

      const run: Run = {
        id: runId, // Use the same ID
        name: newRun.name || 'Untitled Run',
        status: 'active',
        model: newRun.model || 'gemini-3-flash-preview',
        visualStyle: newRun.visualStyle || 'Standard',
        createdAt: new Date().toISOString(),
        shotsCount: 0,
      };

      setRuns(prev => [run, ...prev]);
      setSelectedRunId(run.id);
      setCurrentView(AppView.RUN_EDITOR);
    } catch (error) {
      console.error('Failed to create run:', error);
      alert('Failed to create run. Check console for details.');
    }
  };

  const handleSelectRun = (runId: string) => {
    setSelectedRunId(runId);
    setCurrentView(AppView.RUN_EDITOR);
  };

  return (
    <div className="flex h-screen w-full bg-slate-950 text-slate-100 overflow-hidden">
      <Sidebar
        currentView={currentView}
        onViewChange={setCurrentView}
        activeRunId={selectedRunId}
        runs={runs}
        onSelectRun={handleSelectRun}
      />

      <main className="flex-1 relative overflow-y-auto overflow-x-hidden scroll-smooth">
        {currentView === AppView.DASHBOARD && (
          <Dashboard runs={runs} onSelectRun={handleSelectRun} onNewRun={() => setCurrentView(AppView.WIZARD)} />
        )}

        {currentView === AppView.WIZARD && (
          <RunWizard onCreate={handleCreateRun} onCancel={() => setCurrentView(AppView.DASHBOARD)} />
        )}

        {currentView === AppView.RUN_EDITOR && selectedRunId && (
          <ShotEditor
            runId={selectedRunId}
            runName={runs.find(r => r.id === selectedRunId)?.name || ''}
          />
        )}
      </main>
    </div>
  );
};

export default App;
