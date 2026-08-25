/**
 * API client for interacting with the FastAPI backend.
 */

import {
  AnalysisOverviewDTO,
  DiagramDTO,
  PythonOutputDTO,
} from '../types/workflow';

const BASE_URL = '/api';

export class ApiError extends Error {
  code?: string;
  status: number;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorMsg = `Request failed with status ${res.status}`;
    let code: string | undefined;

    try {
      const errJson = await res.json();
      if (errJson.detail) {
        if (typeof errJson.detail === 'object') {
          errorMsg = errJson.detail.message || errorMsg;
          code = errJson.detail.code;
        } else {
          errorMsg = errJson.detail;
        }
      }
    } catch {
      // Non-JSON response error
    }

    throw new ApiError(errorMsg, res.status, code);
  }

  return res.json() as Promise<T>;
}

export const api = {
  async uploadWorkflow(file: File): Promise<AnalysisOverviewDTO> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${BASE_URL}/upload`, {
      method: 'POST',
      body: formData,
    });

    return handleResponse<AnalysisOverviewDTO>(res);
  },

  async getOverview(analysisId: string): Promise<AnalysisOverviewDTO> {
    const res = await fetch(`${BASE_URL}/analysis/${analysisId}/overview`);
    return handleResponse<AnalysisOverviewDTO>(res);
  },

  async getDiagram(analysisId: string): Promise<DiagramDTO> {
    const res = await fetch(`${BASE_URL}/analysis/${analysisId}/diagram`);
    return handleResponse<DiagramDTO>(res);
  },

  async getToolSummary(analysisId: string, toolId: number): Promise<{ tool_id: number; summary: string; source: string; is_cached: boolean; model: string }> {
    const res = await fetch(`${BASE_URL}/analysis/${analysisId}/tools/${toolId}/summary`);
    return handleResponse<{ tool_id: number; summary: string; source: string; is_cached: boolean; model: string }>(res);
  },

  async getJson(analysisId: string): Promise<Record<string, any>> {
    const res = await fetch(`${BASE_URL}/analysis/${analysisId}/json`);
    return handleResponse<Record<string, any>>(res);
  },

  async getPython(analysisId: string): Promise<PythonOutputDTO> {
    const res = await fetch(`${BASE_URL}/analysis/${analysisId}/python`);
    return handleResponse<PythonOutputDTO>(res);
  },

  getDownloadUrl(analysisId: string, type: 'docx' | 'json' | 'python' | 'svg' | 'zip' | 'sttm'): string {
    return `${BASE_URL}/download/${analysisId}/${type}`;
  },
};
