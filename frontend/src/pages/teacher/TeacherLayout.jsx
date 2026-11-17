import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { roomsApi } from '../../api/services'
import { AppShell, LiveBadge } from '../../components/AppShell'
import { LoadingBlock } from '../../components/common'
import { useAuth } from '../../context/AuthContext'
import { RoomLiveProvider, useRoomEvent } from '../../context/RoomLiveContext'

const TeacherRoomContext = createContext(null)

export function useTeacherRoom() {
  return useContext(TeacherRoomContext)
}

function ActivePollTracker({ onChange }) {
  useRoomEvent((event) => {
    if (event.type === 'poll_started') onChange(event.poll.poll_id)
    if (event.type === 'poll_ended' || event.type === 'poll_cancelled') onChange(null)
  })
  return null
}

export function TeacherLayout() {
  const { room: authRoom, setRoom } = useAuth()
  const [room, setRoomState] = useState(null)
  const [activePollId, setActivePollId] = useState(null)

  const refreshRoom = useCallback(async () => {
    const detail = await roomsApi.mine()
    setRoomState(detail)
    setRoom({ id: detail.id, name: detail.name })
    const live = await roomsApi.activePoll(detail.id)
    setActivePollId(live?.poll_id ?? null)
    return detail
  }, [setRoom])

  useEffect(() => {
    refreshRoom().catch(() => {})
  }, [refreshRoom])

  const value = useMemo(
    () => ({ room, refreshRoom, activePollId, setActivePollId, setRoomState }),
    [room, refreshRoom, activePollId],
  )

  const roomId = room?.id ?? authRoom?.id
  if (!roomId) return <LoadingBlock label="Opening your room…" />

  return (
    <TeacherRoomContext.Provider value={value}>
      <RoomLiveProvider roomId={roomId}>
        <ActivePollTracker onChange={setActivePollId} />
        <AppShell liveBadge={activePollId ? <LiveBadge /> : null} />
      </RoomLiveProvider>
    </TeacherRoomContext.Provider>
  )
}
