import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import { Loader } from 'lucide-react'

interface DashboardStats {
  total_users: number
  active_users: number
  total_resumes: number
  total_requirements: number
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStats()
    // Set up polling for real-time updates every 30 seconds
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchStats = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/admin/dashboard/stats', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setStats(data)
        setError(null)
      } else {
        setError('Failed to fetch dashboard stats')
      }
    } catch (err) {
      setError('Error loading dashboard data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-800">{error}</p>
        <button
          onClick={fetchStats}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-800 mb-6">Admin Dashboard</h1>

      {loading && !stats ? (
        <div className="text-center py-12">
          <div className="inline-block">
            <Loader size={32} className="animate-spin text-blue-600" />
          </div>
          <p className="mt-4 text-gray-600">Loading dashboard data...</p>
        </div>
      ) : stats ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-700 mb-2">Total Users</h3>
            <p className="text-3xl font-bold text-blue-600">{stats.total_users}</p>
            <p className="text-sm text-gray-500 mt-2">Registered profiles</p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-700 mb-2">Active Users</h3>
            <p className="text-3xl font-bold text-green-600">{stats.active_users}</p>
            <p className="text-sm text-gray-500 mt-2">Currently active</p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-700 mb-2">Total Resumes</h3>
            <p className="text-3xl font-bold text-purple-600">{stats.total_resumes}</p>
            <p className="text-sm text-gray-500 mt-2">Profiles parsed</p>
          </div>
        </div>
      ) : null}

      {/* Last Updated indicator */}
      <div className="mt-8 flex items-center justify-between text-sm text-gray-500">
        <p>Auto-refreshes every 30 seconds</p>
        <button
          onClick={fetchStats}
          disabled={loading}
          className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : 'Refresh Now'}
        </button>
      </div>
    </div>
  )
}
