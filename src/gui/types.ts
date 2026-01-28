
export type ShotStatus = 'PLANNED' | 'DONE';

export interface Asset {
  type: 'IMAGE_START' | 'IMAGE_END' | 'CLIP';
  asset_id: string;
  url: string;
  role: 'start_ref' | 'end_ref' | 'final_clip';
}

export interface Shot {
  shot_id: string;
  video_id: string;
  script_text: string;
  intent: string;
  duration_s: number;
  status: ShotStatus;
  assets: Asset[];
  ai_plan?: {
    metaphor: string;
    camera: string;
  };
  prompts?: {
    image_a: string;
    image_b: string;
    video: string;
  };
}

export interface Run {
  id: string;
  name: string;
  status: 'active' | 'completed' | 'draft';
  model: string;
  visualStyle: string;
  createdAt: string;
  shotsCount: number;
}

export enum AppView {
  DASHBOARD = 'DASHBOARD',
  RUN_EDITOR = 'RUN_EDITOR',
  WIZARD = 'WIZARD'
}
