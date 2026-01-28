
import React from 'react';
import { 
  LayoutDashboard, 
  PlusCircle, 
  Settings, 
  Database, 
  History, 
  ChevronRight,
  Zap,
  Activity
} from 'lucide-react';
import { AppView, Run } from '../types';

interface SidebarProps {
  currentView: AppView;
  onViewChange: (view: AppView) => void;
  activeRunId: string | null;
  runs: Run[];
  onSelectRun: (id: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  currentView, 
  onViewChange, 
  activeRunId, 
  runs,
  onSelectRun
}) => {
  return (
    <aside className="w-72 bg-slate-900 border-r border-slate-800 flex flex-col z-20">
      {/* Brand Header */}
      <div className="p-6 border-b border-slate-800 flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <Zap className="text-white fill-white" size={24} />
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight text-white leading-none">THE COCKPIT</h1>
          <p className="text-[10px] text-slate-500 uppercase tracking-widest mt-1 mono font-bold">Mission Control v2.4</p>
        </div>
      </div>

      {/* Primary Navigation */}
      <nav className="p-4 space-y-1">
        <button 
          onClick={() => onViewChange(AppView.DASHBOARD)}
          className={`w-full flex items-center gap-3 px-3 py-2 rounded-md transition-all ${currentView === AppView.DASHBOARD ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
        >
          <LayoutDashboard size={18} />
          <span className="text-sm font-medium">Dashboard</span>
        </button>
        <button 
          onClick={() => onViewChange(AppView.WIZARD)}
          className={`w-full flex items-center gap-3 px-3 py-2 rounded-md transition-all ${currentView === AppView.WIZARD ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
        >
          <PlusCircle size={18} />
          <span className="text-sm font-medium">New Run</span>
        </button>
      </nav>

      {/* Run History Section */}
      <div className="flex-1 overflow-y-auto px-4 py-2 mt-4">
        <div className="flex items-center justify-between mb-3 px-3">
          <div className="flex items-center gap-2 text-[11px] font-bold text-slate-500 uppercase tracking-wider mono">
            <History size={12} />
            Recent Runs
          </div>
        </div>
        <div className="space-y-1">
          {runs.map((run) => (
            <button
              key={run.id}
              onClick={() => onSelectRun(run.id)}
              className={`w-full text-left p-3 rounded-lg transition-all border ${activeRunId === run.id && currentView === AppView.RUN_EDITOR ? 'bg-indigo-950/30 border-indigo-500/50 text-indigo-100' : 'bg-transparent border-transparent text-slate-400 hover:bg-slate-800/50 hover:text-slate-300'}`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] mono font-bold text-slate-500">{run.id}</span>
                {run.status === 'active' && (
                  <span className="flex h-2 w-2 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                )}
              </div>
              <div className="text-xs font-semibold truncate leading-tight">{run.name}</div>
              <div className="text-[10px] opacity-60 mt-1 flex items-center gap-2">
                <Activity size={10} />
                {run.shotsCount} shots
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Footer Settings */}
      <div className="p-4 border-t border-slate-800 space-y-1">
        <button className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-all">
          <Database size={18} />
          <span className="text-sm font-medium">Models & API</span>
        </button>
        <button className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-all">
          <Settings size={18} />
          <span className="text-sm font-medium">Global Config</span>
        </button>
      </div>
    </aside>
  );
};
