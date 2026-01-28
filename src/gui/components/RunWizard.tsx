
import React, { useState, useRef } from 'react';
import { Sparkles, X, FileText, Image, Mic, Zap, Clapperboard, BookOpen, Check } from 'lucide-react';
import { Run } from '../types';

interface RunWizardProps {
  onCreate: (run: Partial<Run>, files: { script: File; styleBible: File; voiceover: File } | null) => void;
  onCancel: () => void;
}

export const RunWizard: React.FC<RunWizardProps> = ({ onCreate, onCancel }) => {
  const [formData, setFormData] = useState({
    name: '',
  });
  const [files, setFiles] = useState<{
    script: File | null;
    styleBible: File | null;
    voiceover: File | null;
  }>({
    script: null,
    styleBible: null,
    voiceover: null,
  });

  const scriptInputRef = useRef<HTMLInputElement>(null);
  const styleBibleInputRef = useRef<HTMLInputElement>(null);
  const voiceoverInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (type: 'script' | 'styleBible' | 'voiceover') => (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFiles(prev => ({ ...prev, [type]: file }));
    }
  };

  const handleCreate = () => {
    if (!formData.name) return;

    // Ensure all files are selected if required, or handle optional uploads
    // For now, we'll require all files or handle logic in parent
    const filesPayload = files.script && files.styleBible && files.voiceover ? {
      script: files.script,
      styleBible: files.styleBible,
      voiceover: files.voiceover
    } : null;

    onCreate({
      ...formData,
      model: 'gemini-3-pro-preview', // Default hidden settings
      visualStyle: 'Cinematic Noir'   // Default hidden settings
    }, filesPayload);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4">
      <div className="bg-slate-900 border border-slate-800 w-full max-w-xl rounded-3xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-300 flex flex-col max-h-[90vh]">
        <header className="p-5 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-indigo-500/10 rounded-lg flex items-center justify-center text-indigo-400 border border-indigo-500/20">
              <Zap size={20} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white leading-none">New Mission Brief</h3>
              <p className="text-[10px] text-slate-500 mono uppercase tracking-widest mt-1">Initialize Production Chain</p>
            </div>
          </div>
          <button onClick={onCancel} className="p-2 text-slate-500 hover:text-white hover:bg-slate-800 rounded-full transition-all">
            <X size={20} />
          </button>
        </header>

        <div className="p-6 overflow-y-auto space-y-8">
          {/* Primary Info */}
          <div className="space-y-2">
            <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mono">Project Mission ID / Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all placeholder:text-slate-700"
              placeholder="e.g., Project AETHELGARD - Cinematic Teaser"
            />
          </div>

          {/* Asset Configuration Grid */}
          <div className="space-y-4">
            <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mono">Core Production Assets</label>
            <div className="grid grid-cols-3 gap-4">
              {/* Script Upload */}
              <div
                onClick={() => scriptInputRef.current?.click()}
                className="bg-slate-950 border border-slate-800 rounded-2xl p-5 flex flex-col items-center justify-center text-slate-600 hover:text-slate-300 hover:border-indigo-500/50 hover:bg-indigo-500/5 transition-all cursor-pointer group relative"
              >
                <input
                  ref={scriptInputRef}
                  type="file"
                  accept=".txt,.md,.pdf"
                  onChange={handleFileChange('script')}
                  className="hidden"
                />
                {files.script && (
                  <div className="absolute top-2 right-2 w-5 h-5 bg-indigo-500 rounded-full flex items-center justify-center">
                    <Check size={12} className="text-white" />
                  </div>
                )}
                <div className="w-12 h-12 rounded-full bg-slate-900 flex items-center justify-center mb-3 group-hover:bg-indigo-900/20 transition-all border border-slate-800 group-hover:border-indigo-500/30">
                  <FileText size={24} className="group-hover:text-indigo-400 transition-colors" />
                </div>
                <span className="text-[10px] font-bold uppercase mono text-center tracking-tight">
                  {files.script ? files.script.name.substring(0, 15) + '...' : 'Script'}
                </span>
              </div>

              {/* Style Bible Upload */}
              <div
                onClick={() => styleBibleInputRef.current?.click()}
                className="bg-slate-950 border border-slate-800 rounded-2xl p-5 flex flex-col items-center justify-center text-slate-600 hover:text-slate-300 hover:border-purple-500/50 hover:bg-purple-500/5 transition-all cursor-pointer group relative"
              >
                <input
                  ref={styleBibleInputRef}
                  type="file"
                  accept=".txt,.md,.pdf"
                  onChange={handleFileChange('styleBible')}
                  className="hidden"
                />
                {files.styleBible && (
                  <div className="absolute top-2 right-2 w-5 h-5 bg-purple-500 rounded-full flex items-center justify-center">
                    <Check size={12} className="text-white" />
                  </div>
                )}
                <div className="w-12 h-12 rounded-full bg-slate-900 flex items-center justify-center mb-3 group-hover:bg-purple-900/20 transition-all border border-slate-800 group-hover:border-purple-500/30">
                  <BookOpen size={24} className="group-hover:text-purple-400 transition-colors" />
                </div>
                <span className="text-[10px] font-bold uppercase mono text-center tracking-tight">
                  {files.styleBible ? files.styleBible.name.substring(0, 15) + '...' : 'Style bible'}
                </span>
              </div>

              {/* Voiceover Upload */}
              <div
                onClick={() => voiceoverInputRef.current?.click()}
                className="bg-slate-950 border border-slate-800 rounded-2xl p-5 flex flex-col items-center justify-center text-slate-600 hover:text-slate-300 hover:border-emerald-500/50 hover:bg-emerald-500/5 transition-all cursor-pointer group relative"
              >
                <input
                  ref={voiceoverInputRef}
                  type="file"
                  accept=".mp3,.wav,.m4a,.aac"
                  onChange={handleFileChange('voiceover')}
                  className="hidden"
                />
                {files.voiceover && (
                  <div className="absolute top-2 right-2 w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                    <Check size={12} className="text-white" />
                  </div>
                )}
                <div className="w-12 h-12 rounded-full bg-slate-900 flex items-center justify-center mb-3 group-hover:bg-emerald-900/20 transition-all border border-slate-800 group-hover:border-emerald-500/30">
                  <Mic size={24} className="group-hover:text-emerald-400 transition-colors" />
                </div>
                <span className="text-[10px] font-bold uppercase mono text-center tracking-tight">
                  {files.voiceover ? files.voiceover.name.substring(0, 15) + '...' : 'Voiceover'}
                </span>
              </div>
            </div>
            <p className="text-[9px] text-slate-500 text-center italic mt-4">Upload these files to let the AI analyze the mission parameters.</p>
          </div>
        </div>

        <footer className="p-5 border-t border-slate-800 bg-slate-950/30 flex items-center justify-between shrink-0">
          <button
            onClick={onCancel}
            className="text-xs font-bold text-slate-500 hover:text-white transition-all px-4 py-2"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!formData.name}
            className="flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white px-8 py-3 rounded-xl text-sm font-bold transition-all shadow-lg shadow-indigo-600/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Clapperboard size={18} /> Launch Production
          </button>
        </footer>
      </div>
    </div>
  );
};
