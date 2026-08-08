// Fetch wrapper providing API communication with the FastAPI backend endpoint.

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function handleResponse(response: Response) {
  if (!response.ok) {
    let errorDetail = 'API Request Failed';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      // Ignore if parsing fails
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export const api = {
  async getProjectSetup() {
    const res = await fetch(`${API_BASE_URL}/api/project-setup`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    return handleResponse(res);
  },

  async updateProjectMeta(meta: any) {
    const res = await fetch(`${API_BASE_URL}/api/project-setup/meta`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(meta),
    });
    return handleResponse(res);
  },

  async updateContractors(contractors: any[]) {
    const res = await fetch(`${API_BASE_URL}/api/project-setup/contractors`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(contractors),
    });
    return handleResponse(res);
  },

  async updateDivisions(divisions: any[]) {
    const res = await fetch(`${API_BASE_URL}/api/project-setup/divisions`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(divisions),
    });
    return handleResponse(res);
  },

  async updateRegulatory(regulatory: any[]) {
    const res = await fetch(`${API_BASE_URL}/api/project-setup/regulatory`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(regulatory),
    });
    return handleResponse(res);
  },

  async updateTasks(tasks: any[]) {
    const res = await fetch(`${API_BASE_URL}/api/project-setup/tasks`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(tasks),
    });
    return handleResponse(res);
  },

  async processSiteEvent(eventText: string) {
    const res = await fetch(`${API_BASE_URL}/api/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ event_text: eventText }),
    });
    return handleResponse(res);
  },
};

