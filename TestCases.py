from flask import Flask, Blueprint, render_template, jsonify, request, session
from model import Hospital, Doctor, DoctorAppointments
from extension import db
import datetime
import unittest

app = Flask(__name__)

hospital_dashboard = Blueprint('hospital_dashboard', __name__)


# Routes for hospital dashboard
@hospital_dashboard.route('/hospital_dashboard', methods=['GET', 'POST'])
def hospdashboard():
    if 'hospital_id' in session:
        hospital_id = session['hospital_id']
        hospital = Hospital.query.get(hospital_id)
        doctors = hospital.doctors
        return render_template('hospital_dashboard.html', hospital=hospital, doctors=doctors)
    else:
        return render_template('hospital_login.html')


@hospital_dashboard.route('/save_doctors', methods=['POST'])
def save_doctors():
    try:
        data = request.json
        if 'doctorIds' not in data:
            raise ValueError('Doctor IDs not provided in the request.')

        selected_doctor_ids = data['doctorIds']

        # Update doctor availability status in the database
        Doctor.query.filter(Doctor.doctorId.in_(selected_doctor_ids)).update({'availabilityStatus': True})
        Doctor.query.filter(~Doctor.doctorId.in_(selected_doctor_ids)).update({'availabilityStatus': False})
        db.session.commit()

        return jsonify({'message': 'Doctors availability updated successfully'}), 200
    except Exception as e:
        print(f"Error occurred while updating doctors availability: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update doctors availability. Please try again.'}), 500


# Utility function to generate appointment slots for a doctor
def generate_appointment_slots(doctor_id):
    # Generate appointment slots for the new doctor
    appointment_slots = []
    # Example: Generate slots for 8 AM to 5 PM with 30-minute intervals
    start_time = datetime.time(8, 0)
    end_time = datetime.time(17, 0)
    interval = datetime.timedelta(minutes=30)
    current_time = datetime.datetime.combine(datetime.date.today(), start_time)
    while current_time <= datetime.datetime.combine(datetime.date.today(), end_time):
        appointment_slots.append(current_time.time())
        current_time += interval

    # Insert generated slots into the database
    for slot in appointment_slots:
        new_appointment = DoctorAppointments(doctorId=doctor_id, appointmentSlots=slot, appointmentAvailable=True)
        db.session.add(new_appointment)
    db.session.commit()


# Routes for managing appointment slots
@hospital_dashboard.route('/get_appointment_slots', methods=['GET'])
def get_appointment_slots():
    try:
        doctor_id = request.args.get('doctorId')
        if not doctor_id:
            raise ValueError('Doctor ID not provided in the request.')

        # Fetch appointment slots for the specified doctor ID
        appointment_slots = DoctorAppointments.query.filter_by(doctorId=doctor_id).all()

        # Prepare the slots data to send back to the client
        slots_data = [{'slotId': slot.appointmentId, 'appointmentSlots': str(slot.appointmentSlots)} for slot in
                      appointment_slots]

        return jsonify({'appointmentSlots': slots_data}), 200
    except Exception as e:
        print(f"Error occurred while fetching appointment slots: {e}")
        return jsonify({'error': 'Failed to fetch appointment slots. Please try again.'}), 500


@hospital_dashboard.route('/save_appointment_slots', methods=['POST'])
def save_appointment_slots():
    try:
        data = request.json
        if 'doctorId' not in data or 'selectedSlots' not in data:
            raise ValueError('Doctor ID or selected slots not provided in the request.')

        doctor_id = data['doctorId']
        selected_slots = data['selectedSlots']

        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            raise ValueError('Doctor not found with ID: {}'.format(doctor_id))

        doctor.appointmentSlots = selected_slots

        DoctorAppointments.query.filter_by(doctorId=doctor_id).update({'appointmentAvailable': False})

        # Set appointmentAvailable to True for selected slots
        DoctorAppointments.query.filter(DoctorAppointments.appointmentId.in_(selected_slots)).update(
            {'appointmentAvailable': True})
        db.session.commit()

        return jsonify({'message': 'Appointment slots saved successfully'}), 200
    except Exception as e:
        print(f"Error occurred while saving appointment slots: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to save appointment slots. Please try again.'}), 500


# Routes for doctor management
@hospital_dashboard.route('/register_doctor', methods=['POST'])
def register_doctor():
    try:
        data = request.json
        doctor_name = data['doctorName']
        category = data['category']
        hospital_id = session.get('hospital_id')

        availability_status = True

        new_doctor = Doctor(doctorName=doctor_name, category=category, hospitalId=hospital_id,
                            availabilityStatus=availability_status)

        db.session.add(new_doctor)
        db.session.commit()
        generate_appointment_slots(new_doctor.doctorId)

        return jsonify({'message': 'Doctor registered successfully'}), 200
    except Exception as e:
        print(f"Error occurred while registering the new doctor: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to register the new doctor. Please try again.'}), 500


@hospital_dashboard.route('/delete_doctor', methods=['POST'])
def delete_doctor():
    try:
        data = request.json
        if 'doctorId' not in data:
            raise ValueError('Doctor ID not provided in the request.')

        doctor_id = data['doctorId']
        doctor = Doctor.query.get(doctor_id)

        if not doctor:
            raise ValueError('Doctor not found with the provided ID.')

        db.session.delete(doctor)
        db.session.commit()

        return jsonify({'message': 'Doctor deleted successfully'}), 200
    except Exception as e:
        print(f"Error occurred while deleting doctor: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete the doctor. Please try again.'}), 500


@hospital_dashboard.route('/edit_doctor', methods=['POST'])
def edit_doctor():
    try:
        data = request.json
        if 'doctorId' not in data or 'newName' not in data or 'newCategory' not in data:
            raise ValueError('Doctor ID, new name, or new category not provided in the form data.')

        doctor_id = data['doctorId']
        new_name = data['newName']
        new_category = data['newCategory']

        doctor = Doctor.query.get(doctor_id)

        if not doctor:
            raise ValueError('Doctor not found with the provided ID.')

        doctor.doctorName = new_name
        doctor.category = new_category

        db.session.commit()

        return jsonify({'message': 'Doctor details updated successfully'}), 200
    except Exception as e:
        print(f"Error occurred while updating doctor details: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update doctor details. Please try again.'}), 500


@hospital_dashboard.route('/api/doctors', methods=['GET'])
def get_doctors():
    try:
        category = request.args.get('category')
        doctors = Doctor.query.filter_by(category=category).all()
        doctor_data = [{'doctorId': doctor.doctorId, 'doctorName': doctor.doctorName, 'category': doctor.category,
                        'availabilityStatus': doctor.availabilityStatus} for doctor in doctors]
        return jsonify(doctor_data), 200
    except Exception as e:
        print(f"Error occurred while fetching doctors: {e}")
        return jsonify({'error': 'Failed to fetch doctors. Please try again.'}), 500


# Register the hospital dashboard blueprint
app.register_blueprint(hospital_dashboard)


# Define a test class inheriting from unittest.TestCase
class TestHospitalDashboard(unittest.TestCase):
    def setUp(self):
        """Set up the test app and create a test database."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        db.create_all()

    def tearDown(self):
        """Clean up after each test."""
        db.session.remove()
        db.drop_all()

    # Define test methods to test specific functionalities
    def test_hospital_dashboard_route_with_session(self):
        """Test hospital_dashboard route when session is present."""
        with self.app as client:
            with client.session_transaction() as sess:
                sess['hospital_id'] = 1  # Set session variable
            response = client.get('/hospital_dashboard')
            self.assertEqual(response.status_code, 200)

    def test_hospital_dashboard_route_without_session(self):
        """Test hospital_dashboard route when session is not present."""
        response = self.app.get('/hospital_dashboard')
        self.assertEqual(response.status_code, 200)  # Assuming it should return 200 even without session

    def test_save_doctors_route(self):
        """Test save_doctors route."""
        with self.app as client:
            response = client.post('/save_doctors', json={'doctorIds': [1, 2, 3]})
            self.assertEqual(response.status_code, 200)

            # Check if doctors' availability status is updated correctly
            doctors = Doctor.query.all()
            for doctor in doctors:
                if doctor.doctorId in [1, 2, 3]:
                    self.assertTrue(doctor.availabilityStatus)
                else:
                    self.assertFalse(doctor.availabilityStatus)


# Conditional block to run tests only if the script is executed directly
if __name__ == '__main__':
    # Load tests from the test class
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestHospitalDashboard)

    # Run tests using a test runner
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Output results
    if result.wasSuccessful():
        print("All tests passed successfully!")
    else:
        print("Some tests failed.")