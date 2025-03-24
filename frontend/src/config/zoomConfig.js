export const zoomConfig = {
  apiKey: import.meta.env.VITE_ZOOM_SDK_KEY,
  meetingNumber: '',
  userName: '',
  userEmail: '',
  password: '',
  signature: '',
};

export const generateSignature = async (meetingNumber, role) => {
  try {
    const response = await fetch('http://localhost:8000/api/generate-signature/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        meeting_number: meetingNumber,
        role: role,
      }),
    });
    const data = await response.json();
    return data.signature;
  } catch (error) {
    console.error('Error generating signature:', error);
    throw error;
  }
}; 