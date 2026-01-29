import React, { useState, useEffect } from 'react';
import { Upload, X, FileText, Trash2, Loader } from 'lucide-react';

interface Resume {
  resume_id: number;
  user_id: number;
  file_name: string;
  file_size: number;
  file_type: string;
  skills?: string[];
  created_at?: string;
  is_active: boolean;
  views_count: number;
}

interface ResumeUploadProps {
  userId: number;
}

export const ResumeUpload: React.FC<ResumeUploadProps> = ({ userId }) => {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    fetchResumes();
  }, [userId]);

  const fetchResumes = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/users/resumes/${userId}`);
      if (!response.ok) throw new Error('Failed to fetch resumes');
      const data = await response.json();
      setResumes(data.resumes || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error loading resumes');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const file = files[0];
    if (!file.name.endsWith('.pdf')) {
      setError('Only PDF files are supported');
      return;
    }

    try {
      setUploading(true);
      setError(null);

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`/api/users/resume/upload/${userId}`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data = await response.json();
      setResumes([...resumes, data.resume]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (resumeId: number) => {
    try {
      const response = await fetch(`/api/users/resume/${resumeId}/${userId}`, {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to delete resume');

      setResumes(resumes.filter((r) => r.resume_id !== resumeId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  const handleDrag = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    handleUpload(e.dataTransfer.files);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString?: string): string => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-lg p-8">
      <h2 className="text-2xl font-bold mb-6">Resume Management</h2>

      {error && (
        <div className="mb-4 p-4 bg-red-100 text-red-700 rounded-lg flex justify-between items-center">
          <span>{error}</span>
          <button onClick={() => setError(null)}>
            <X size={20} />
          </button>
        </div>
      )}

      {/* Upload Area */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition ${
          dragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <input
          type="file"
          accept=".pdf"
          onChange={(e) => handleUpload(e.target.files)}
          disabled={uploading}
          className="hidden"
          id="resume-input"
        />
        <label htmlFor="resume-input" className="cursor-pointer block">
          {uploading ? (
            <>
              <Loader className="mx-auto mb-2 animate-spin text-blue-600" size={32} />
              <p className="text-blue-600 font-semibold">Uploading...</p>
            </>
          ) : (
            <>
              <Upload className="mx-auto mb-2 text-gray-400" size={32} />
              <p className="text-lg font-semibold">Drag & drop your resume here</p>
              <p className="text-gray-600 text-sm mt-2">or click to select a PDF file</p>
            </>
          )}
        </label>
      </div>

      {/* Resumes List */}
      <div className="mt-8">
        <h3 className="text-lg font-semibold mb-4">
          Your Resumes ({resumes.length})
        </h3>

        {loading ? (
          <div className="text-center py-8">
            <Loader className="mx-auto animate-spin text-blue-600" size={32} />
          </div>
        ) : resumes.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <FileText className="mx-auto mb-2" size={32} />
            <p>No resumes uploaded yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {resumes.map((resume) => (
              <div
                key={resume.resume_id}
                className="border rounded-lg p-4 flex justify-between items-center hover:bg-gray-50 transition"
              >
                <div className="flex items-center gap-3 flex-1">
                  <FileText className="text-red-600" size={24} />
                  <div className="flex-1">
                    <p className="font-semibold">{resume.file_name}</p>
                    <p className="text-sm text-gray-600">
                      {formatFileSize(resume.file_size)} • Uploaded{' '}
                      {formatDate(resume.created_at)} • {resume.views_count} views
                    </p>
                    {resume.skills && resume.skills.length > 0 && (
                      <div className="flex gap-2 mt-2 flex-wrap">
                        {resume.skills.slice(0, 3).map((skill, idx) => (
                          <span
                            key={idx}
                            className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded"
                          >
                            {skill}
                          </span>
                        ))}
                        {resume.skills.length > 3 && (
                          <span className="text-xs text-gray-500">
                            +{resume.skills.length - 3} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(resume.resume_id)}
                  className="p-2 hover:bg-red-100 text-red-600 rounded-lg transition"
                  title="Delete resume"
                >
                  <Trash2 size={20} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
