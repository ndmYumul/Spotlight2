import React, { useState, useEffect, useCallback } from 'react'
import { Container, Row, Col, Card, Form, Button, Table, Badge, Spinner, Alert, ListGroup } from 'react-bootstrap'
import { useSelector, useDispatch } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import Message from '../components/Message'
import { updateUserSchedule, getUserDetails } from '../actions/userActions'

function ScheduleScreen() {
    const navigate = useNavigate()
    const dispatch = useDispatch()

    const [buildings, setBuildings] = useState([])
    const [tierList, setTierList] = useState([]) 
    const [syncLoading, setSyncLoading] = useState(false)
    const [clearLoading, setClearLoading] = useState(false)
    const [tierLoading, setTierLoading] = useState(false)
    const [syncMessage, setSyncMessage] = useState(null)
    const [overflows, setOverflows] = useState([]) 

    const [days, setDays] = useState([
        { id: 1, day: 'Monday', arrival: '08:00', departure: '17:00', active: true, building: '' },
        { id: 2, day: 'Tuesday', arrival: '08:00', departure: '17:00', active: true, building: '' },
        { id: 3, day: 'Wednesday', arrival: '08:00', departure: '17:00', active: true, building: '' },
        { id: 4, day: 'Thursday', arrival: '08:00', departure: '17:00', active: true, building: '' },
        { id: 5, day: 'Friday', arrival: '08:00', departure: '17:00', active: true, building: '' },
        { id: 6, day: 'Saturday', arrival: '08:00', departure: '12:00', active: false, building: '' },
        { id: 7, day: 'Sunday', arrival: '08:00', departure: '12:00', active: false, building: '' },
    ])

    const userLogin = useSelector(state => state.userLogin)
    const { userInfo } = userLogin

    const userScheduleUpdate = useSelector(state => state.userScheduleUpdate)
    const { loading, error, success } = userScheduleUpdate

    const refreshScreenData = useCallback(async () => {
        try {
            const { data: bData } = await axios.get('/api/buildings/')
            setBuildings(bData)
            
            const config = { headers: { Authorization: `Bearer ${userInfo.token}` } }
            const { data: uData } = await axios.get('/api/users/profile/', config)
            
            if (uData.preferences && uData.preferences.length > 0) {
                setTierList(uData.preferences)
            } else {
                setTierList(bData.map(b => b.name))
            }

            dispatch(getUserDetails('profile'))
        } catch (err) {
            console.error("Refresh failed:", err)
        }
    }, [dispatch, userInfo])

    useEffect(() => {
        if (!userInfo) {
            navigate('/login')
        } else {
            refreshScreenData()
            if (userInfo?.schedule?.weekly_schedule) {
                setDays(userInfo.schedule.weekly_schedule)
            }
        }
    }, [userInfo, navigate, refreshScreenData])

    const moveItem = (index, direction) => {
        const newList = [...tierList]
        const newIndex = direction === 'up' ? index - 1 : index + 1
        if (newIndex < 0 || newIndex >= newList.length) return
        
        const temp = newList[index]
        newList[index] = newList[newIndex]
        newList[newIndex] = temp
        setTierList(newList)
    }

    const saveTierList = async () => {
        setTierLoading(true)
        try {
            const config = { headers: { Authorization: `Bearer ${userInfo.token}` } }
            await axios.put('/api/users/profile/update/', { 'preferences': tierList }, config)
            setSyncMessage({ variant: 'success', text: 'Building Priority Tierlist Saved!' })
            refreshScreenData()
        } catch (err) {
            setSyncMessage({ variant: 'danger', text: 'Failed to update preferences.' })
        }
        setTierLoading(false)
    }

    const handleToggle = (id) => {
        if (!userInfo?.isPro && !userInfo?.isAdmin) return
        setDays(days.map(d => d.id === id ? { ...d, active: !d.active } : d))
    }

    const handleFieldChange = (id, field, value) => {
        if (!userInfo?.isPro && !userInfo?.isAdmin) return
        setDays(days.map(d => d.id === id ? { ...d, [field]: value } : d))
    }

    const submitHandler = async (e) => {
        e.preventDefault()
        await dispatch(updateUserSchedule({ weekly_schedule: days }))
        refreshScreenData()
    }

    const handleReserveAll = async () => {
        setSyncLoading(true)
        setSyncMessage(null)
        setOverflows([])
        try {
            const config = { headers: { Authorization: `Bearer ${userInfo.token}` } }
            
            // Sync local state to DB first
            await dispatch(updateUserSchedule({ weekly_schedule: days }))
            
            // Trigger automated allocation logic
            const { data } = await axios.post('/api/users/schedule/weekly-sync/', {}, config)
            
            setSyncMessage({ variant: 'success', text: data.message })
            if (data.overflow_warnings) {
                setOverflows(data.overflow_warnings)
            }
            
            refreshScreenData()
        } catch (err) {
            setSyncMessage({ 
                variant: 'danger', 
                text: err.response?.data?.error || 'Sync Failed' 
            })
        }
        setSyncLoading(false)
    }

    const handleClearAll = async () => {
        if (!window.confirm("Delete all upcoming reservations?")) return
        setClearLoading(true)
        try {
            const config = { headers: { Authorization: `Bearer ${userInfo.token}` } }
            const { data } = await axios.post('/api/users/schedule/clear-weekly/', {}, config)
            setSyncMessage({ variant: 'info', text: data.message })
            refreshScreenData()
        } catch (err) {
            setSyncMessage({ variant: 'danger', text: 'Clear Failed' })
        }
        setClearLoading(false)
    }

    const applyToAllActive = (buildingName) => {
        setDays(days.map(d => d.active ? { ...d, building: buildingName } : d));
    }

    return (
        <Container className="py-4">
            <Row>
                {(userInfo?.isPro || userInfo?.isAdmin) && (
                    <Col lg={3} className="mb-4">
                        <Card className="shadow-sm border-0 rounded-4 p-3 bg-white sticky-top" style={{ top: '20px' }}>
                            <h5 className="fw-bold mb-3">
                                <i className="fas fa-sort-amount-down text-warning me-2"></i>Tierlist
                            </h5>
                            <p className="small text-muted">Rank buildings by priority for automated overflow.</p>
                            
                            <ListGroup variant="flush" className="mb-3 border rounded overflow-hidden">
                                {tierList.map((name, index) => (
                                    <ListGroup.Item key={index} className="d-flex justify-content-between align-items-center py-2 px-2 bg-light border-bottom">
                                        <div className="d-flex align-items-center">
                                            <Badge bg="warning" text="dark" className="me-2">{index + 1}</Badge>
                                            <span className="small fw-bold">{name}</span>
                                        </div>
                                        <div className="d-flex gap-1">
                                            <Button size="sm" variant="white" className="py-0 px-1 border shadow-sm" onClick={() => moveItem(index, 'up')} disabled={index === 0}>
                                                <i className="fas fa-arrow-up text-muted x-small"></i>
                                            </Button>
                                            <Button size="sm" variant="white" className="py-0 px-1 border shadow-sm" onClick={() => moveItem(index, 'down')} disabled={index === tierList.length - 1}>
                                                <i className="fas fa-arrow-down text-muted x-small"></i>
                                            </Button>
                                        </div>
                                    </ListGroup.Item>
                                ))}
                            </ListGroup>
                            
                            <Button variant="warning" size="sm" className="w-100 fw-bold shadow-sm" onClick={saveTierList} disabled={tierLoading}>
                                {tierLoading ? <Spinner size="sm" /> : 'Update Tierlist'}
                            </Button>
                        </Card>
                    </Col>
                )}

                <Col lg={(userInfo?.isPro || userInfo?.isAdmin) ? 9 : 12}>
                    <div className="d-flex align-items-center mb-4 p-3 rounded-4 shadow-sm bg-white border-start border-5 border-warning">
                        <div className="me-3">
                            <i className={`fas ${userInfo?.isPro || userInfo?.isAdmin ? 'fa-crown text-warning' : 'fa-user text-secondary'} fa-2x`}></i>
                        </div>
                        <div className="flex-grow-1">
                            <h5 className="mb-0 fw-bold">{userInfo?.isPro || userInfo?.isAdmin ? 'Spotlight Pro Member' : 'Basic Student Plan'}</h5>
                            <small className="text-muted">
                                {userInfo?.isPro || userInfo?.isAdmin ? 'Waterfall Priority Enabled.' : 'Upgrade to rank your favorite buildings.'}
                            </small>
                        </div>
                    </div>

                    {success && <Message variant="success">Schedule Saved!</Message>}
                    {syncMessage && <Alert variant={syncMessage.variant} onClose={() => setSyncMessage(null)} dismissible>{syncMessage.text}</Alert>}
                    
                    {overflows.length > 0 && (
                        <Alert variant="warning" className="rounded-4 shadow-sm border-0">
                            <h6 className="fw-bold"><i className="fas fa-exclamation-triangle me-2"></i>Availability Alerts:</h6>
                            <ul className="mb-0 small">
                                {overflows.map((note, idx) => <li key={idx}>{note}</li>)}
                            </ul>
                        </Alert>
                    )}

                    {error && <Message variant="danger">{error}</Message>}

                    <Card className="shadow-sm border-0 rounded-4 p-4 mb-4 position-relative">
                        {!userInfo?.isPro && !userInfo?.isAdmin && (
                            <div className="position-absolute top-0 start-0 w-100 h-100 d-flex flex-column align-items-center justify-content-center rounded-4" 
                                 style={{ backgroundColor: 'rgba(255, 255, 255, 0.7)', zIndex: 10, backdropFilter: 'blur(5px)' }}>
                                <i className="fas fa-lock fa-3x text-warning mb-3"></i>
                                <h3 className="fw-bold">Pro Feature</h3>
                                <Button variant="warning" className="fw-bold px-4 shadow" onClick={() => navigate('/subscription')}>Upgrade to Unlock</Button>
                            </div>
                        )}

                        <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-3">
                            <h2 className="fw-bold mb-0">Weekly Routine</h2>
                            <div className="d-flex gap-2">
                                <Button variant="outline-danger" size="sm" className="fw-bold" onClick={handleClearAll} disabled={clearLoading || syncLoading}>
                                    {clearLoading ? <Spinner size="sm" /> : 'Clear Reservations'}
                                </Button>
                                <Button variant="primary" size="sm" className="fw-bold text-white shadow-sm" onClick={handleReserveAll} disabled={syncLoading || clearLoading || (!userInfo?.isPro && !userInfo?.isAdmin)}>
                                    {syncLoading ? <Spinner size="sm" /> : 'Sync with AI'}
                                </Button>
                                <Button variant="warning" size="sm" className="fw-bold shadow-sm" onClick={submitHandler} disabled={loading || (!userInfo?.isPro && !userInfo?.isAdmin)}>
                                    {loading ? <Spinner size="sm" /> : 'Update Schedule'}
                                </Button>
                            </div>
                        </div>

                        {(userInfo?.isPro || userInfo?.isAdmin) && (
                            <div className="mb-4 p-3 bg-light rounded-3 d-flex align-items-center justify-content-between border">
                                <div className="small fw-bold text-muted text-uppercase">Quick Fill:</div>
                                <Form.Select 
                                    size="sm" 
                                    className="w-auto border-warning shadow-sm" 
                                    onChange={(e) => applyToAllActive(e.target.value)}
                                >
                                    <option value="">Select building for all active days...</option>
                                    <option value="">✨ Use Tierlist Priority</option>
                                    <hr />
                                    {buildings.map(b => (
                                        <option key={b._id} value={b.name}>{b.name} ({b.slots} left)</option>
                                    ))}
                                </Form.Select>
                            </div>
                        )}

                        <Table responsive hover className="align-middle border-top">
                            <thead>
                                <tr className="text-muted small text-uppercase">
                                    <th>Active</th>
                                    <th>Day</th>
                                    <th>Target Building</th>
                                    <th>In</th>
                                    <th>Out</th>
                                </tr>
                            </thead>
                            <tbody>
                                {days.map((d) => (
                                    <tr key={d.id} className={!d.active ? 'opacity-50 grayscale' : ''}>
                                        <td>
                                            <Form.Check 
                                                type="switch" 
                                                id={`switch-${d.id}`}
                                                checked={d.active} 
                                                onChange={() => handleToggle(d.id)} 
                                            />
                                        </td>
                                        <td className="fw-bold">{d.day}</td>
                                        <td>
                                            <Form.Select 
                                                size="sm"
                                                value={d.building} 
                                                disabled={!d.active} 
                                                onChange={(e) => handleFieldChange(d.id, 'building', e.target.value)}
                                            >
                                                <option value="">Tierlist Priority</option>
                                                {buildings.map(b => (
                                                    <option key={b._id} value={b.name}>{b.name}</option>
                                                ))}
                                            </Form.Select>
                                        </td>
                                        <td>
                                            <Form.Control size="sm" type="time" value={d.arrival} disabled={!d.active} onChange={(e) => handleFieldChange(d.id, 'arrival', e.target.value)} />
                                        </td>
                                        <td>
                                            <Form.Control size="sm" type="time" value={d.departure} disabled={!d.active} onChange={(e) => handleFieldChange(d.id, 'departure', e.target.value)} />
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </Table>
                    </Card>

                    <Card className="shadow-sm border-0 rounded-4 p-4 bg-light">
                        <div className="d-flex justify-content-between align-items-center mb-3">
                            <h5 className="fw-bold mb-0">Current Assignments</h5>
                            {userInfo?.schedule?.updated_at && (
                                <Badge bg="white" className="text-muted border">
                                    Last Sync: {new Date(userInfo.schedule.updated_at).toLocaleTimeString('en-PH')}
                                </Badge>
                            )}
                        </div>
                        <Row>
                            {days.filter(d => d.active).map(d => (
                                <Col key={d.id} xs={12} sm={6} md={4} className="mb-2">
                                    <div className="p-2 px-3 bg-white rounded-3 border shadow-sm">
                                        <div className="d-flex justify-content-between">
                                            <span className="small fw-bold">{d.day}</span>
                                            <i className="fas fa-check-circle text-success small"></i>
                                        </div>
                                        <div className="text-primary fw-bold small">
                                            {d.building || 'Tierlist Priority'}
                                        </div>
                                    </div>
                                </Col>
                            ))}
                        </Row>
                    </Card>
                </Col>
            </Row>
        </Container>
    )
}

export default ScheduleScreen;