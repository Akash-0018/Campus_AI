import React, { useState, useEffect } from 'react';
import { User, Mail, Phone, Camera, Save, X } from 'lucide-react';

interface UserProfileData {
  user_id: number;
  username: string;
  email: string;
  full_name: string;
  role: string;
  bio?: string;
  phone_number?: string;
  profile_image_url?: string;
  is_verified: boolean;
  created_at: string;
}

interface UserProfileProps {
  userId: number;
  onClose?: () => void;
}

export const UserProfile: React.FC<UserProfileProps> = ({ userId, onClose }) => {
  const [profile, setProfile] = useState<UserProfileData | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    full_name: '',
    phone_number: '',
    bio: '',
    profile_image_url: '',
  });

  useEffect(() => {
    fetchProfile();
  }, [userId]);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/users/${userId}`);
      if (!response.ok) throw new Error('Failed to fetch profile');
      const data = await response.json();
      setProfile(data);
      setFormData({
        full_name: data.full_name || '',
        phone_number: data.phone_number || '',
        bio: data.bio || '',
        profile_image_url: data.profile_image_url || '',
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error loading profile');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    try {
      const response = await fetch(`/api/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (!response.ok) throw new Error('Failed to update profile');
      const updated = await response.json();
      setProfile(updated);
      setIsEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error updating profile');
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // In a real app, you'd upload to cloud storage and get a URL back
    const reader = new FileReader();
    reader.onloadend = () => {
      setFormData({
        ...formData,
        profile_image_url: reader.result as string,
      });
    };
    reader.readAsDataURL(file);
  };

  if (loading) return <div className="p-8 text-center">Loading profile...</div>;
  if (error) return <div className="p-8 text-center text-red-600">{error}</div>;
  if (!profile) return <div className="p-8 text-center">Profile not found</div>;

  return (
    <div className="max-w-2xl mx-auto bg-white rounded-lg shadow-lg p-8">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Profile</h1>
        {onClose && (
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full"
          >
            <X size={24} />
          </button>
        )}
      </div>

      {/* Profile Image Section */}
      <div className="flex justify-center mb-8">
        <div className="relative">
          <div className="w-32 h-32 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center overflow-hidden">
            {formData.profile_image_url ? (
              <img
                src={formData.profile_image_url}
                alt="Profile"
                className="w-full h-full object-cover"
              />
            ) : (
              <User size={64} className="text-white" />
            )}
          </div>
          {isEditing && (
            <label className="absolute bottom-0 right-0 bg-blue-600 text-white p-2 rounded-full cursor-pointer hover:bg-blue-700">
              <Camera size={20} />
              <input
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
              />
            </label>
          )}
        </div>
      </div>

      {/* Profile Information */}
      {!isEditing ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-gray-600 text-sm">Full Name</label>
              <p className="text-lg font-semibold">{profile.full_name}</p>
            </div>
            <div>
              <label className="text-gray-600 text-sm">Username</label>
              <p className="text-lg font-semibold">{profile.username}</p>
            </div>
          </div>

          <div>
            <label className="text-gray-600 text-sm flex items-center gap-2">
              <Mail size={16} /> Email
            </label>
            <p className="text-lg">{profile.email}</p>
          </div>

          <div>
            <label className="text-gray-600 text-sm flex items-center gap-2">
              <Phone size={16} /> Phone
            </label>
            <p className="text-lg">
              {profile.phone_number || 'Not provided'}
            </p>
          </div>

          <div>
            <label className="text-gray-600 text-sm">Bio</label>
            <p className="text-lg">{profile.bio || 'No bio provided'}</p>
          </div>

          <div className="flex gap-2 pt-4 border-t">
            <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
              {profile.role}
            </span>
            {profile.is_verified && (
              <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                Verified
              </span>
            )}
          </div>

          <button
            onClick={() => setIsEditing(true)}
            className="w-full mt-6 bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition"
          >
            Edit Profile
          </button>
        </div>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSaveProfile();
          }}
          className="space-y-6"
        >
          <div>
            <label className="text-gray-700 text-sm font-semibold">Full Name</label>
            <input
              type="text"
              value={formData.full_name}
              onChange={(e) =>
                setFormData({ ...formData, full_name: e.target.value })
              }
              className="w-full mt-2 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="text-gray-700 text-sm font-semibold">Email</label>
            <input
              type="email"
              value={profile.email}
              disabled
              className="w-full mt-2 px-4 py-2 border rounded-lg bg-gray-100 text-gray-500"
            />
          </div>

          <div>
            <label className="text-gray-700 text-sm font-semibold">Phone</label>
            <input
              type="tel"
              value={formData.phone_number}
              onChange={(e) =>
                setFormData({ ...formData, phone_number: e.target.value })
              }
              className="w-full mt-2 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="text-gray-700 text-sm font-semibold">Bio</label>
            <textarea
              value={formData.bio}
              onChange={(e) =>
                setFormData({ ...formData, bio: e.target.value })
              }
              rows={4}
              className="w-full mt-2 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Tell others about yourself..."
            />
          </div>

          <div className="flex gap-3 pt-4 border-t">
            <button
              type="submit"
              className="flex-1 bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition flex items-center justify-center gap-2"
            >
              <Save size={20} /> Save Changes
            </button>
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="flex-1 bg-gray-300 text-gray-700 py-3 rounded-lg hover:bg-gray-400 transition"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
