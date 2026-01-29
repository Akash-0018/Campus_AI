import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserProfile } from './UserProfile';
import { ResumeUpload } from './ResumeUpload';
import { ProfileSearch } from './ProfileSearch';
import { User, Upload, Search, LogOut, Settings, Menu, X, Home, BookOpen } from 'lucide-react';

interface UserDashboardProps {
  userId: number;
  username?: string;
  onLogout?: () => void;
}

type Tab = 'profile' | 'resumes' | 'search';

export const UserDashboard: React.FC<UserDashboardProps> = ({
  userId,
  username,
  onLogout,
}) => {
  const [activeTab, setActiveTab] = useState<Tab>('profile');
  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const navigate = useNavigate();

  const handleLogout = () => {
    onLogout?.();
    navigate('/login');
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode; description: string }[] = [
    { id: 'profile', label: 'Profile', icon: <User size={24} />, description: 'View and edit your profile' },
    { id: 'resumes', label: 'Resumes', icon: <Upload size={24} />, description: 'Manage your resumes' },
    { id: 'search', label: 'Search', icon: <Search size={24} />, description: 'Find other profiles' },
  ];

  return (
    <div className="min-h-screen bg-gray-100 flex">
      {/* Sidebar */}
      <div
        className={`${
          sidebarOpen ? 'w-64' : 'w-20'
        } bg-gradient-to-b from-blue-700 to-blue-900 text-white transition-all duration-300 flex flex-col shadow-lg`}
      >
        {/* Logo Section */}
        <div className="p-6 border-b border-blue-600 flex items-center justify-between">
          <div className={`flex items-center gap-3 ${!sidebarOpen && 'justify-center w-full'}`}>
            <div className="w-10 h-10 rounded-lg bg-blue-500 flex items-center justify-center font-bold text-lg">
              CA
            </div>
            {sidebarOpen && <span className="text-xl font-bold">Campus AI</span>}
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex-1 p-4 space-y-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                setSelectedProfileId(null);
              }}
              className={`w-full flex items-center gap-4 px-4 py-3 rounded-lg transition-all ${
                activeTab === tab.id
                  ? 'bg-blue-500 shadow-lg'
                  : 'hover:bg-blue-600'
              }`}
              title={!sidebarOpen ? tab.label : undefined}
            >
              <div className="flex-shrink-0">{tab.icon}</div>
              {sidebarOpen && (
                <div className="flex-1 text-left">
                  <div className="font-semibold text-sm">{tab.label}</div>
                  <div className="text-xs text-blue-200">
                    {tab.description}
                  </div>
                </div>
              )}
            </button>
          ))}
        </nav>

        {/* User Section */}
        <div className="p-4 border-t border-blue-600 space-y-2">
          <div className={`px-4 py-2 rounded-lg bg-blue-600 ${!sidebarOpen && 'hidden'}`}>
            <p className="text-xs text-blue-200">Logged in as</p>
            <p className="font-semibold truncate">{username}</p>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-red-600 transition-colors"
          >
            <LogOut size={24} />
            {sidebarOpen && <span>Logout</span>}
          </button>
        </div>

        {/* Toggle Button */}
        <div className="p-4 border-t border-blue-600">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center justify-center p-2 rounded-lg hover:bg-blue-600 transition-colors"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Header */}
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="px-8 py-4 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">
                {tabs.find(t => t.id === activeTab)?.label}
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                {tabs.find(t => t.id === activeTab)?.description}
              </p>
            </div>
            <div className="flex items-center gap-4">
              <button className="p-2 hover:bg-gray-100 rounded-lg text-gray-600 transition">
                <Settings size={20} />
              </button>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto p-8">
          <div className="animate-fadeIn">
            {activeTab === 'profile' && (
              <UserProfile userId={userId} />
            )}

            {activeTab === 'resumes' && (
              <ResumeUpload userId={userId} />
            )}

            {activeTab === 'search' && (
              <div className="grid grid-cols-1 gap-8">
                <ProfileSearch
                  userId={userId}
                  onProfileClick={(profileId) => {
                    setSelectedProfileId(profileId);
                  }}
                />
              </div>
            )}
          </div>
        </main>
      </div>

      {/* Selected Profile Modal */}
      {selectedProfileId && selectedProfileId !== userId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-auto relative">
            <button
              onClick={() => setSelectedProfileId(null)}
              className="sticky top-4 right-4 z-10 p-2 bg-white hover:bg-gray-100 rounded-full shadow-lg float-right m-4"
            >
              ✕
            </button>
            <div className="p-8">
              <UserProfile userId={selectedProfileId} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
