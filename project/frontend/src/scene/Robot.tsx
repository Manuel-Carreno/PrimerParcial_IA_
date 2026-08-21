import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import type { Group } from 'three'
import { useSimStore } from '../store/simStore'

export function Robot() {
  const group = useRef<Group>(null)
  const pos = useSimStore(
    (s) => s.runtime?.robotPosition ?? ([0, 0.35, 0] as [number, number, number]),
  )
  const yaw = useSimStore((s) => s.runtime?.robotYaw ?? 0)

    const celebra = useSimStore((s) => {
    if (!s.scenario || !s.runtime) return false
    if (s.running || s.plan.length === 0) return false
    if (s.stepIndex < s.plan.length) return false
    return s.scenario.goal.stations_online.every(
      (id) => s.runtime!.stations[id] === 'ONLINE',
    )
  })

    useFrame((state) => {
    if (!group.current) return
    const t = state.clock.getElapsedTime()

    group.current.position.x = pos[0]
    group.current.position.z = pos[2]

    if (celebra) {
      group.current.position.y = pos[1] + Math.abs(Math.sin(t * 5)) * 0.28
      group.current.rotation.y += 0.06
    } else {
      group.current.position.y = pos[1]
      group.current.rotation.y = yaw
    }
  })

  const acento = celebra ? '#4ade80' : '#22d3ee'
  const brillo = celebra ? '#16a34a' : '#0891b2'

  return (
    <group ref={group} position={[pos[0], pos[1], pos[2]]} rotation={[0, yaw, 0]}>
      <mesh position={[0, 0.15, 0]}>
        <boxGeometry args={[0.55, 0.4, 0.55]} />
        <meshStandardMaterial color="#f1f5f9" roughness={0.35} metalness={0.2} />
      </mesh>
      <mesh position={[0, 0.4, 0]}>
        <boxGeometry args={[0.45, 0.12, 0.45]} />
        <meshStandardMaterial color="#e2e8f0" />
      </mesh>

      {/* ojo izquierdo */}
      <mesh position={[-0.12, 0.24, 0.29]}>
        <sphereGeometry args={[0.055, 16, 16]} />
        <meshStandardMaterial color="#000000" emissive="#000000" emissiveIntensity={1.4} />
      </mesh>
      {/* ojo derecho */}
      <mesh position={[0.12, 0.24, 0.29]}>
        <sphereGeometry args={[0.055, 16, 16]} />
        <meshStandardMaterial color="#000000" emissive="#000000" emissiveIntensity={1.4} />
      </mesh>
      {/* sonrisa */}
      <mesh position={[0, 0.14, 0.29]} rotation={[0, 0, Math.PI]}>
        <torusGeometry args={[0.11, 0.022, 12, 24, Math.PI]} />
        <meshStandardMaterial color="#000000" emissive="#000000" emissiveIntensity={1.4} />
      </mesh>

      {[
        [-0.22, -0.02, -0.22],
        [0.22, -0.02, -0.22],
        [-0.22, -0.02, 0.22],
        [0.22, -0.02, 0.22],
      ].map((p, i) => (
        <mesh key={i} position={p as [number, number, number]}>
          <boxGeometry args={[0.12, 0.1, 0.12]} />
          <meshStandardMaterial color="#0f172a" />
        </mesh>
      ))}
    </group>
  )
}