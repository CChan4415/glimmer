import { useCallback, useEffect, useState } from 'react'
import GraphView from '../components/GraphView'
import api from '../services/api'
import { useAuth } from '../auth/AuthContext'

const GROUP_LABELS = { family: '家人', colleague: '同事', friend: '朋友', ungrouped: '未分组', center: '我' }

export default function GraphPage() {
  const { user, logout } = useAuth()
  const [graphData, setGraphData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const [secondDegreeNodes, setSecondDegreeNodes] = useState([])
  const [expandMsg, setExpandMsg] = useState('')
  const [expandedIds, setExpandedIds] = useState(new Set())
  const [expanding, setExpanding] = useState(false)

  const loadGraph = useCallback(async () => {
    try {
      setLoading(true)
      const { data } = await api.get('/me/graph')
      setGraphData(data.data)
      setError('')
    } catch (e) {
      setError(e.response?.data?.detail || '加载关系图失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadGraph() }, [loadGraph])

  const handleNodeClick = (node) => {
    setSelected(node)
    setExpandMsg('')
  }

  const collapseAll = () => {
    setSelected(null)
    setSecondDegreeNodes([])
    setExpandedIds(new Set())
    setExpandMsg('')
  }

  const expandSecondDegree = async (node) => {
    setExpandMsg('')
    setExpanding(true)
    if (!node.is_registered) {
      setExpanding(false)
      setExpandMsg('对方尚未注册，无法查看 TA 的朋友')
      return
    }
    try {
      const res = await api.get(`/me/network/second-degree/${node.id}`)
      const nodes = res.data.data || []
      // Attach source contact id so the graph can draw the edge
      const withSource = nodes.map((n) => ({ ...n, source_contact_id: node.id }))
      setSecondDegreeNodes((prev) => [...prev, ...withSource])
      if (!expandedIds.has(node.id)) {
        setExpandedIds(new Set([...expandedIds, node.id]))
      }
      if (nodes.length === 0) {
        setExpandMsg('TA 的朋友暂未公开')
      }
    } catch (e) {
      setExpandMsg(e.response?.data?.detail || '加载失败')
    } finally {
      setExpanding(false)
    }
  }

  const expandAll = async () => {
    const registered = graphData?.nodes.filter((n) => n.is_registered && n.degree === 1) || []
    if (registered.length === 0) {
      setExpandMsg('暂无已注册的联系人可展开')
      return
    }
    setExpandMsg('')
    for (const node of registered) {
      await expandSecondDegree(node)
    }
  }

  return (
    <div className="graph-page">
      <header className="topbar">
        <div className="brand">流萤 Glimmer</div>
        <div className="actions">
          <button className="btn-ghost" onClick={expandAll} disabled={expanding}>
            {expanding ? '展开中...' : '展开全部 2 度'}
          </button>
          <button className="btn-ghost" onClick={collapseAll}>收起全部</button>
          <span className="user-chip">{user?.nickname || '我'}</span>
          <button className="btn-ghost" onClick={logout}>退出</button>
        </div>
      </header>

      {loading && <div className="loading">加载关系图...</div>}
      {error && <div className="error-bar">{error} <button onClick={loadGraph}>重试</button></div>}

      {graphData && !loading && (
        <div className="main-area">
          <div className="graph-wrap">
            <GraphView
              graphData={graphData}
              secondDegreeNodes={secondDegreeNodes}
              onNodeClick={handleNodeClick}
            />
            {expanding && (
              <div className="graph-loading">
                <span className="spinner" />
                展开关系网中...
              </div>
            )}
          </div>

          <aside className="side-panel">
            {!selected && (
              <div className="stats-card">
                <h3>关系资产</h3>
                <div className="stats-grid">
                  <Stat label="总数" value={graphData.stats.total_contacts} />
                  <Stat label="家人" value={graphData.stats.family} color="#e8456b" />
                  <Stat label="同事" value={graphData.stats.colleague} color="#12a5a0" />
                  <Stat label="朋友" value={graphData.stats.friend} color="#f2a33c" />
                  <Stat label="未分组" value={graphData.stats.ungrouped} color="#8a8fa3" />
                </div>
                {Object.keys(graphData.stats.by_tag).length > 0 && (
                  <>
                    <h4>热门标签</h4>
                    <div className="tag-cloud">
                      {Object.entries(graphData.stats.by_tag).map(([tag, count]) => (
                        <span key={tag} className="tag-chip">{tag} {count}</span>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {selected && (
              <div className="detail-card">
                <h3>{selected.name || selected.display_name}</h3>
                <p className="group-label">{GROUP_LABELS[selected.group] || selected.group}</p>
                {selected.degree === 1 && selected.tags?.length > 0 && (
                  <div className="tag-cloud">
                    {selected.tags.map((t) => <span key={t} className="tag-chip">{t}</span>)}
                  </div>
                )}
                {selected.degree === 2 && <p className="muted">这是朋友的 2 度联系人（化名展示）</p>}

                <div className="detail-actions">
                  {selected.degree === 1 && (
                    <button className="btn-primary" onClick={() => expandSecondDegree(selected)}>
                      查看 TA 的朋友
                    </button>
                  )}
                </div>
              </div>
            )}

            {expandMsg && (
              <div className="expand-msg">
                <p className="muted">{expandMsg}</p>
              </div>
            )}
          </aside>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, color }) {
  return (
    <div className="stat">
      <div className="stat-value" style={color ? { color } : {}}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}
