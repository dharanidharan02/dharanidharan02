from flask import Blueprint, render_template, request, jsonify, session
from model import Appointment, Doctor, Hospital, DoctorAppointments,db

appointment = Blueprint('appointment', __name__)


@appointment.route('/api/user_appointments', methods=['GET'])
def get_user_appointments():
    # Get user ID from session
    user_id = session.get('id')

    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    # Fetch appointments for the specified user ID
    user_appointments = Appointment.query.filter_by(user_id=user_id).all()

    # Convert appointments to a list of dictionaries
    appointments_data = [{'id': appointment.id, 'time': appointment.time.strftime('%H:%M')} for appointment in user_appointments]

    return jsonify(appointments_data)


@appointment.route('/search_appointments', methods=['POST'])
def search_appointments():
    search_data = request.json.get('searchValue', '').strip()

    # Fetch appointments matching the search term
    appointments = Appointment.query.filter(Appointment.id.ilike(f'%{search_data}%')).all()

    # Prepare the response data
    appointments_data = []
    for appointment in appointments:
        print(appointments)
        # Fetch doctor appointment record associated with the appointment ID
        print('hi')
        doctor_appointment = DoctorAppointments.query.filter_by(appointmentId=appointment.appointment_id).first()
        print(doctor_appointment)
        if doctor_appointment:
            # Fetch doctor record using doctor ID from doctor appointment record
            doctor = Doctor.query.get(doctor_appointment.doctorId)
            print(doctor)
            if doctor:
                # Fetch hospital record using hospital ID from doctor record
                hospital = Hospital.query.get(doctor.hospitalId)
                if hospital:
                    # Add appointment details to the response data
                    appointments_data.append({
                        'id': appointment.id,
                        'time': appointment.time.strftime('%H:%M'),  # Assuming time is a datetime object
                        'doctor_name': doctor.doctorName,
                        'category': doctor.category,  # Assuming category is a column in the Doctor table
                        'hospital_name': hospital.hospitalName
                    })

    return jsonify(appointments_data)

@appointment.route('/cancel_appointment', methods=['POST'])
def cancel_appointment():
    try:
        data = request.json
        appointment_id = data.get('appointmentId')

        # Retrieve appointment from the database
        appointment = Appointment.query.get(appointment_id)

        if appointment:

            appointment_id = appointment.appointment_id

            db.session.delete(appointment)
            db.session.commit()

            # Update the availability status of the corresponding doctor in the doctor_appointment table
            print(appointment_id)
            doctor_appointment = DoctorAppointments.query.filter_by(appointmentId=appointment_id).first()
            if doctor_appointment:
                doctor_appointment.doctor.appointmentAvailable = True
                db.session.commit()

            # Return success response
            return jsonify({'message': 'Appointment cancelled successfully'}), 200
        else:
            return jsonify({'error': 'Appointment not found'}), 404
    except Exception as e:
        print(f"Error cancelling appointment: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to cancel appointment. Please try again.'}), 500
