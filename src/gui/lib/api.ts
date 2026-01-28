// API client for connecting to the backend
const API_BASE = '/api';

export interface Run {
    run_id: string;
    version: number;
    video_id: string;
    created_at: string;
    status?: {
        current_stage: string;
        stage_status: string;
        updated_at: string;
        progress_current?: number;
        progress_total?: number;
        progress_message?: string;
    };
}

export interface Shot {
    shot_id: string;
    run_id: string;
    version: number;
    video_id: string;
    script_text: string;
    intent: string;
    metaphor?: string;
    camera_config?: string;
    duration_s: number;
    beat_start_s?: number;
    beat_end_s?: number;
    status: 'PLANNED' | 'DONE';
    assets: Asset[];
}

export interface Asset {
    asset_id: string;
    shot_id: string;
    type: 'PROMPT' | 'IMAGE_START' | 'IMAGE_END' | 'CLIP';
    role?: string;
    path?: string;
    url?: string;
    metadata?: string;
    created_at: string;
    is_selected: boolean;
}

export const api = {
    async getRuns(): Promise<Run[]> {
        const response = await fetch(`${API_BASE}/runs`);
        if (!response.ok) throw new Error('Failed to fetch runs');
        return response.json();
    },

    async getRunStatus(runId: string, version: number = 1): Promise<Run['status']> {
        const response = await fetch(`${API_BASE}/runs/${runId}/status?version=${version}`);
        if (!response.ok) throw new Error('Failed to fetch run status');
        return response.json();
    },

    async getShots(runId: string, version: number = 1): Promise<Shot[]> {
        const response = await fetch(`${API_BASE}/runs/${runId}/shots?version=${version}`);
        if (!response.ok) throw new Error('Failed to fetch shots');
        return response.json();
    },

    async getShot(runId: string, shotId: string, version: number = 1): Promise<Shot> {
        const response = await fetch(`${API_BASE}/runs/${runId}/shots/${shotId}?version=${version}`);
        if (!response.ok) throw new Error('Failed to fetch shot');
        return response.json();
    },

    async generateImages(runId: string, shotId: string, version: number = 1, videoId: string = 'VID_001') {
        const response = await fetch(`${API_BASE}/runs/${runId}/shots/${shotId}/generate-images?version=${version}&video_id=${videoId}`, {
            method: 'POST',
        });
        if (!response.ok) throw new Error('Failed to generate images');
        return response.json();
    },

    async generateClip(runId: string, shotId: string, version: number = 1, videoId: string = 'VID_001') {
        const response = await fetch(`${API_BASE}/runs/${runId}/shots/${shotId}/generate-clips?version=${version}&video_id=${videoId}`, {
            method: 'POST',
        });
        if (!response.ok) throw new Error('Failed to generate clip');
        return response.json();
    },

    async createRun(runId: string, videoId: string, files: { script: File; styleBible: File; voiceover: File }, version: number = 1) {
        const formData = new FormData();
        formData.append('run_id', runId);
        formData.append('video_id', videoId);
        formData.append('version', version.toString());
        formData.append('script', files.script);
        formData.append('style_bible', files.styleBible);
        formData.append('voiceover', files.voiceover);

        const response = await fetch(`${API_BASE}/runs/create`, {
            method: 'POST',
            body: formData,
        });
        if (!response.ok) throw new Error('Failed to create run');
        return response.json();
    },

    async executeStage(runId: string, stage: string, videoId: string, version: number = 1) {
        const response = await fetch(`${API_BASE}/runs/${runId}/stages/${stage}/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ version, video_id: videoId }),
        });
        if (!response.ok) throw new Error(`Failed to execute stage ${stage}`);
        return response.json();
    },
};
