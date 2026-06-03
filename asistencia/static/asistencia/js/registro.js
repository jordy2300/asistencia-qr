/* ── Flujo de registro móvil ── */

const csrf = document.getElementById('csrf').value;
let geoLat = null, geoLng = null;

// Obtener geolocalización al cargar
window.addEventListener('load', () => {
  const geoStatus = document.getElementById('geo-status');
  if (!navigator.geolocation) {
    geoStatus.textContent = '❌ GPS no disponible en este dispositivo';
    geoStatus.className = 'geo-status geo-error';
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      geoLat = pos.coords.latitude;
      geoLng = pos.coords.longitude;
      geoStatus.textContent = '✅ Ubicación obtenida';
      geoStatus.className = 'geo-status geo-ok';
    },
    (err) => {
      geoStatus.textContent = '❌ No se pudo obtener ubicación. Active el GPS.';
      geoStatus.className = 'geo-status geo-error';
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
});

function setError(id, msg) {
  document.getElementById(id).textContent = msg;
}

async function verificarCedula() {
  const cedula = document.getElementById('cedula').value.trim();
  setError('error-msg', '');

  if (!cedula) { setError('error-msg', 'Ingrese su número de cédula.'); return; }
  if (!geoLat || !geoLng) { setError('error-msg', 'Esperando GPS. Asegúrese de tener el GPS activo.'); return; }

  const btn = document.getElementById('btn-continuar');
  btn.disabled = true;
  btn.textContent = 'Verificando…';

  const data = new FormData();
  data.append('csrfmiddlewaretoken', csrf);
  data.append('cedula', cedula);
  data.append('latitud', geoLat);
  data.append('longitud', geoLng);

  try {
    const res = await fetch('/registrar/cedula/', { method: 'POST', body: data });
    const json = await res.json();

    if (json.ok) {
      document.getElementById('celular-display', ).textContent = json.celular;
      document.getElementById('nombre-display').textContent = json.nombre;
      if (json.otp_dev) {
        const hint = document.getElementById('otp-dev');
        hint.textContent = `[DEV] Su código: ${json.otp_dev}`;
        hint.classList.remove('hidden');
      }
      document.getElementById('step-cedula').classList.add('hidden');
      document.getElementById('step-otp').classList.remove('hidden');
      startOtpTimer(5 * 60);
    } else {
      setError('error-msg', json.error);
    }
  } catch (e) {
    setError('error-msg', 'Error de conexión. Intente nuevamente.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Continuar →';
  }
}

async function confirmarOtp() {
  const codigo = document.getElementById('otp').value.trim();
  setError('error-otp', '');
  if (!codigo || codigo.length < 6) { setError('error-otp', 'Ingrese el código de 6 dígitos.'); return; }

  const data = new FormData();
  data.append('csrfmiddlewaretoken', csrf);
  data.append('codigo', codigo);

  try {
    const res = await fetch('/registrar/otp/', { method: 'POST', body: data });
    const json = await res.json();

    if (json.ok) {
      document.getElementById('nombre-exito').textContent = json.nombre;
      document.getElementById('fecha-exito').textContent = json.fecha;
      document.getElementById('hora-exito').textContent = json.hora;
      if (json.tarde) document.getElementById('tarde-aviso').classList.remove('hidden');
      document.getElementById('step-otp').classList.add('hidden');
      document.getElementById('step-exito').classList.remove('hidden');
    } else {
      setError('error-otp', json.error);
    }
  } catch (e) {
    setError('error-otp', 'Error de conexión.');
  }
}

let timerInterval = null;
function startOtpTimer(seconds) {
  clearInterval(timerInterval);
  const el = document.getElementById('otp-timer');
  timerInterval = setInterval(() => {
    if (seconds <= 0) {
      clearInterval(timerInterval);
      el.textContent = '⏰ Código expirado. Regrese y solicite uno nuevo.';
      el.style.color = '#C0392B';
      return;
    }
    const m = Math.floor(seconds / 60), s = seconds % 60;
    el.textContent = `⏱ Válido por ${m}:${String(s).padStart(2,'0')}`;
    seconds--;
  }, 1000);
}
