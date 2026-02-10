import { useEffect, useState } from "react"
import axios from 'axios'

export const MapSelector = ({ onMapSwitch }) => {
    const [maps, setMaps] = useState({})
    const [currentMap, setCurrentMap] = useState('unknown')
    const [loading, setLoading] = useState(false)
    const [switching, setSwitching] = useState(false)

    const fetchMaps = async () => {
        setLoading(true)
        try {
            const response = await axios.get('/map/list-available', { params: { _: Date.now() } })
            setMaps(response.data.maps)
            setCurrentMap(response.data.current_map)
            console.log('[MapSelector] list-available', response.data.current_map)
        } catch (error) {
            console.error('[MapSelector] Failed to fetch maps:', error)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        // Fetch once on mount. No automatic polling to avoid interrupting user interaction.
        fetchMaps()
    }, [])

    const handleMapSwitch = async (mapKey) => {
        if (mapKey === currentMap) return

        setSwitching(true)
        try {
            console.log('[MapSelector] switching map', mapKey)
            const response = await axios.get('/map/switch', { params: { map_key: mapKey, _: Date.now() } })
            if (response.data.success) {
                console.log('[MapSelector] switch success', response.data)
                setCurrentMap(mapKey)
                // Notify parent component to refresh map
                if (onMapSwitch) {
                    onMapSwitch(mapKey)
                }
                // Trigger a refresh of the map list after switch
                setTimeout(async () => {
                    await fetchMaps()
                    console.log('[MapSelector] refreshed current_map', mapKey)
                    setSwitching(false)
                }, 500)
            } else {
                console.error('[MapSelector] switch failed', response.data)
                alert(`Failed to switch map: ${response.data.error}`)
                setSwitching(false)
            }
        } catch (error) {
            console.error('[MapSelector] Failed to switch map:', error)
            alert('Error switching map')
            setSwitching(false)
        }
    }

    return (
        <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <label className="block mb-2 text-sm font-medium text-gray-900 dark:text-white">
                Select Map
            </label>
            <div className="flex gap-2">
                <select
                    value={currentMap}
                    onChange={(e) => handleMapSwitch(e.target.value)}
                    disabled={switching || loading}
                    className="flex-1 px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-75 disabled:cursor-not-allowed"
                >
                    {Object.entries(maps).map(([key, map]) => (
                        <option key={key} value={key} title={map.description}>
                            {map.name}
                        </option>
                    ))}
                </select>

                <button
                    className="ml-2 px-3 py-2 btn btn-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg"
                    onClick={() => fetchMaps()}
                    disabled={loading}
                    title="Refresh map list"
                >
                    {loading ? 'Refreshing...' : 'Refresh'}
                </button>

                {switching && (
                    <div className="flex items-center px-3 py-2">
                        <svg aria-hidden="true" role="status" className="w-4 h-4 text-blue-500 animate-spin" viewBox="0 0 100 101" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z" fill="#E5E7EB"/>
                            <path d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z" fill="currentColor"/>
                        </svg>
                    </div>
                )}
            </div>
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                {maps[currentMap]?.description}
            </p>
        </div>
    )
}

export default MapSelector
