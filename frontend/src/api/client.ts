/**
 * API client for interacting with the FastAPI backend.
 */

import {
  AnalysisOverviewDTO,
  DiagramDTO,
  PythonOutputDTO,
} from '../types/workflow';
import { PortfolioOverviewDTO, RationalisationAnalysisDTO } from '../types/portfolio';

const BASE_URL = '/api';

export function isPortfolioResponse(data: any): data is PortfolioOverviewDTO {
  return data && typeof data === 'object' && 'portfolio_id' in data;
}

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
  async uploadWorkflow(file: File): Promise<AnalysisOverviewDTO | PortfolioOverviewDTO> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${BASE_URL}/upload`, {
      method: 'POST',
      body: formData,
    });

    return handleResponse<AnalysisOverviewDTO | PortfolioOverviewDTO>(res);
  },

  async uploadPortfolio(files: File[], relativePaths?: string[], portfolioName: string = "ETL Portfolio"): Promise<PortfolioOverviewDTO | AnalysisOverviewDTO> {
    const formData = new FormData();
    files.forEach((f) => {
      formData.append('files', f);
    });
    if (relativePaths && relativePaths.length > 0) {
      relativePaths.forEach((p) => {
        formData.append('relative_paths', p);
      });
    }
    formData.append('portfolio_name', portfolioName);

    const res = await fetch(`${BASE_URL}/portfolio/upload`, {
      method: 'POST',
      body: formData,
    });

    return handleResponse<PortfolioOverviewDTO | AnalysisOverviewDTO>(res);
  },

  async getPortfolio(portfolioId: string): Promise<PortfolioOverviewDTO> {
    const res = await fetch(`${BASE_URL}/portfolio/${portfolioId}`);
    return handleResponse<PortfolioOverviewDTO>(res);
  },

  async getPortfolioWorkflow(portfolioId: string, workflowId: string): Promise<AnalysisOverviewDTO> {
    const res = await fetch(`${BASE_URL}/portfolio/${portfolioId}/workflow/${workflowId}`);
    return handleResponse<AnalysisOverviewDTO>(res);
  },

  async getPortfolioRationalisation(portfolioId: string, useLlm: boolean = true): Promise<RationalisationAnalysisDTO> {
    const res = await fetch(`${BASE_URL}/portfolio/${portfolioId}/rationalisation?use_llm=${useLlm}`);
    return handleResponse<RationalisationAnalysisDTO>(res);
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

  getDownloadUrl(analysisId: string, type: 'docx' | 'technical-docx' | 'tool-specifications' | 'json' | 'python' | 'svg' | 'zip' | 'sttm'): string {
    return `${BASE_URL}/download/${analysisId}/${type}`;
  },

  async downloadFile(analysisId: string, type: 'docx' | 'technical-docx' | 'tool-specifications' | 'json' | 'python' | 'svg' | 'zip' | 'sttm'): Promise<void> {
    const url = `${BASE_URL}/download/${analysisId}/${type}`;
    const res = await fetch(url);

    if (!res.ok) {
      let errorMsg = `Download failed with status ${res.status}`;
      try {
        const errJson = await res.json();
        if (errJson.detail) {
          errorMsg = typeof errJson.detail === 'object' ? errJson.detail.message || errorMsg : errJson.detail;
        }
      } catch {
        // Non-JSON response error
      }
      throw new ApiError(errorMsg, res.status);
    }

    const blob = await res.blob();
    const disposition = res.headers.get('Content-Disposition') || '';
    let filename = `download.${type === 'technical-docx' || type === 'docx' ? 'docx' : type}`;
    
    const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
    if (filenameMatch && filenameMatch[1]) {
      filename = filenameMatch[1];
    }

    const blobUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(blobUrl);
  },
};

export const apiClient = api;

