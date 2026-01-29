/**
 * Campus AI API Service
 * Centralized API client for all backend communications
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiService {
  // ============================================================================
  // USER PROFILE ENDPOINTS
  // ============================================================================

  async getUser(userId: number) {
    const response = await fetch(`${API_BASE_URL}/api/users/${userId}`);
    if (!response.ok) throw new Error('Failed to fetch user');
    return response.json();
  }

  async updateUser(userId: number, data: {
    full_name?: string;
    phone_number?: string;
    bio?: string;
    profile_image_url?: string;
  }) {
    const response = await fetch(`${API_BASE_URL}/api/users/${userId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update user');
    return response.json();
  }

  async listAllUsers(skip = 0, limit = 100) {
    const response = await fetch(
      `${API_BASE_URL}/api/users/admin/list?skip=${skip}&limit=${limit}`
    );
    if (!response.ok) throw new Error('Failed to list users');
    return response.json();
  }

  // ============================================================================
  // RESUME ENDPOINTS
  // ============================================================================

  async uploadResume(userId: number, file: File) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(
      `${API_BASE_URL}/api/users/resume/upload/${userId}`,
      {
        method: 'POST',
        body: formData,
      }
    );
    if (!response.ok) throw new Error('Failed to upload resume');
    return response.json();
  }

  async getUserResumes(userId: number) {
    const response = await fetch(
      `${API_BASE_URL}/api/users/resumes/${userId}`
    );
    if (!response.ok) throw new Error('Failed to fetch resumes');
    return response.json();
  }

  async deleteResume(resumeId: number, userId: number) {
    const response = await fetch(
      `${API_BASE_URL}/api/users/resume/${resumeId}/${userId}`,
      { method: 'DELETE' }
    );
    if (!response.ok) throw new Error('Failed to delete resume');
    return response.json();
  }

  async getAllResumes() {
    const response = await fetch(
      `${API_BASE_URL}/api/users/admin/all-resumes`
    );
    if (!response.ok) throw new Error('Failed to fetch all resumes');
    return response.json();
  }

  async bulkUploadResumes(files: File[]) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    const response = await fetch(
      `${API_BASE_URL}/api/users/admin/resume/bulk-upload`,
      {
        method: 'POST',
        body: formData,
      }
    );
    if (!response.ok) throw new Error('Failed to bulk upload resumes');
    return response.json();
  }

  // ============================================================================
  // SEARCH / CHATBOT ENDPOINTS
  // ============================================================================

  async searchProfiles(query: string, userId?: number) {
    const response = await fetch(
      `${API_BASE_URL}/api/users/search/profiles`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          user_id: userId,
        }),
      }
    );
    if (!response.ok) throw new Error('Failed to search profiles');
    return response.json();
  }

  async getDirectory(excludeUserId?: number) {
    const params = excludeUserId
      ? `?exclude_user_id=${excludeUserId}`
      : '';
    const response = await fetch(
      `${API_BASE_URL}/api/users/directory${params}`
    );
    if (!response.ok) throw new Error('Failed to fetch directory');
    return response.json();
  }

  async recordProfileView(resumeId: number) {
    const response = await fetch(
      `${API_BASE_URL}/api/users/profile/${resumeId}/view`,
      {
        method: 'POST',
      }
    );
    if (!response.ok) throw new Error('Failed to record view');
    return response.json();
  }

  // ============================================================================
  // HEALTH CHECK
  // ============================================================================

  async healthCheck() {
    const response = await fetch(`${API_BASE_URL}/api/users/health`);
    if (!response.ok) throw new Error('Health check failed');
    return response.json();
  }
}

export const apiService = new ApiService();
