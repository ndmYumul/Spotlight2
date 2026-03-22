import React, { useEffect, useState } from 'react' 
import { Table, Button, Container, Row, Col, Card, Badge, Modal, Form } from 'react-bootstrap'
import { useDispatch, useSelector } from 'react-redux'
import Loader from '../components/Loader'
import Message from '../components/Message'
import LiveClock from '../components/LiveClock'
import { listReservations, deleteReservation, updateReservation } from '../actions/reservationActions'
import { RESERVATION_UPDATE_RESET } from '../constants/reservationConstants'

function AdminReservationListScreen() {
    const dispatch = useDispatch()

    const [show, setShow] = useState(false)
    const [selectedRes, setSelectedRes] = useState({})
    const [startHour, setStartHour] = useState(0)
    const [filter, setFilter] = useState('All')

    const { loading, error, reservations } = useSelector(state => state.reservationList)
    const { success: successUpdate } = useSelector(state => state.reservationUpdate)
    const { success: successDelete } = useSelector(state => state.reservationDelete)

    useEffect(() => {
        if (successUpdate) {
            dispatch({ type: RESERVATION_UPDATE_RESET })
            setShow(false)
        }
        dispatch(listReservations())
    }, [dispatch, successUpdate, successDelete])

    const handleEdit = (reservation) => {
        setSelectedRes(reservation)
        setStartHour(reservation.start_hour)
        setShow(true)
    }

    const submitHandler = (e) => {
        e.preventDefault()
        dispatch(updateReservation({
            _id: selectedRes._id,
            start_hour: startHour,
            end_hour: Number(startHour) + 1 
        }))
    }

    const deleteHandler = (id) => {
        if (window.confirm('Are you sure you want to delete this reservation?')) {
            dispatch(deleteReservation(id))
        }
    }

    const format24h = (hour) => `${hour < 10 ? '0' + hour : hour}:00`

    const filteredReservations = reservations?.filter(res => {
        if (filter === 'Active') return !res.is_completed
        if (filter === 'Completed') return res.is_completed
        return true
    })

    return (
        <Container>
            <Row className="align-items-center my-4">
                <Col md={5}>
                    <h1 className="fw-bold">
                        <i className="fas fa-calendar-check me-2 text-warning"></i>Reservations
                    </h1>
                </Col>
                <Col md={3}>
                    <Form.Select 
                        value={filter} 
                        onChange={(e) => setFilter(e.target.value)}
                        className="shadow-sm border-0 bg-light"
                    >
                        <option value="All">All Status</option>
                        <option value="Active">Active Only</option>
                        <option value="Completed">Completed Only</option>
                    </Form.Select>
                </Col>
                <Col md={4} className="text-end">
                    <LiveClock />
                </Col>
            </Row>

            <Card className="shadow-sm border-0 overflow-hidden">
                <Card.Body className="p-0">
                    {loading ? <Loader /> : error ? <Message variant='danger'>{error}</Message> : (
                        <Table hover responsive className='table-sm mb-0 align-middle'>
                            <thead className="table-dark">
                                <tr>
                                    <th className="p-3">STUDENT</th>
                                    <th className="p-3">DATE</th>
                                    <th className="p-3">SLOT</th>
                                    <th className="p-3 text-center">STATUS</th>
                                    <th className="p-3 text-center">ACTIONS</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredReservations?.map(reservation => (
                                    <tr key={reservation._id} className={reservation.is_completed ? 'opacity-75' : ''}>
                                        <td className="p-3">
                                            <div className="fw-bold">{reservation.userName}</div>
                                            <small className="text-muted">{reservation.buildingName}</small>
                                        </td>
                                        <td className="p-3">{reservation.date}</td>
                                        <td className="p-3">
                                            <Badge bg="secondary" className="me-1">{format24h(reservation.start_hour)}</Badge>
                                            <i className="fas fa-arrow-right fa-xs mx-1 text-muted"></i>
                                            <Badge bg="secondary">{format24h(reservation.end_hour)}</Badge>
                                        </td>
                                        <td className="p-3 text-center">
                                            <Badge bg={reservation.is_completed ? 'light' : 'success'} className={reservation.is_completed ? 'text-dark border' : ''}>
                                                {reservation.is_completed ? 'COMPLETED' : 'ACTIVE'}
                                            </Badge>
                                        </td>
                                        <td className="p-3 text-center">
                                            <Button 
                                                variant='outline-primary' 
                                                className='btn-sm me-2' 
                                                onClick={() => handleEdit(reservation)} 
                                                disabled={reservation.is_completed}
                                            >
                                                <i className='fas fa-edit'></i>
                                            </Button>
                                            <Button 
                                                variant='outline-danger' 
                                                className='btn-sm' 
                                                onClick={() => deleteHandler(reservation._id)}
                                            >
                                                <i className='fas fa-trash'></i>
                                            </Button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </Table>
                    )}
                </Card.Body>
            </Card>

            <Modal show={show} onHide={() => setShow(false)} centered>
                <Modal.Header closeButton>
                    <Modal.Title>Edit Reservation Time</Modal.Title>
                </Modal.Header>
                <Form onSubmit={submitHandler}>
                    <Modal.Body>
                        <Form.Group controlId='startHour'>
                            <Form.Label>New Arrival Hour (24h Format)</Form.Label>
                            <Form.Control 
                                type='number' 
                                min="0" 
                                max="23" 
                                value={startHour} 
                                onChange={(e) => setStartHour(e.target.value)}
                            />
                        </Form.Group>
                    </Modal.Body>
                    <Modal.Footer>
                        <Button variant="secondary" onClick={() => setShow(false)}>Close</Button>
                        <Button variant="warning" type="submit">Save Changes</Button>
                    </Modal.Footer>
                </Form>
            </Modal>
        </Container>
    )
}

export default AdminReservationListScreen