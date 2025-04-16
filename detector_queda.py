import cv2
import mediapipe as mp
import numpy as np
import time
import serial

# === Inicializa comunicação com o Arduino ===
arduino = serial.Serial('COM6', 9600)
time.sleep(2)

# === Inicialização do MediaPipe ===
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_draw = mp.solutions.drawing_utils

# === Variáveis de controle ===
tempo_inicio_queda = None
tempo_queda_confirmada = 1 
queda_confirmada = False
contador_quedas = 0

# === Carrega vídeo ===
cap = cv2.VideoCapture("video.mp4")

while True:
    ret, frame = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue

    frame = cv2.resize(frame, (500, 500))
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    resultado = pose.process(rgb)

    nova_queda_confirmada = False

    if resultado.pose_landmarks:
        mp_draw.draw_landmarks(frame, resultado.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        pontos = resultado.pose_landmarks.landmark

        h, w = frame.shape[:2]
        nariz = pontos[0]
        quadril = pontos[24]
        joelho = pontos[26]

        nariz_y = nariz.y * h
        quadril_y = quadril.y * h
        joelho_y = joelho.y * h

        limiar_chao = h * 0.85
        tolerancia = 50

        deitado = (
            nariz_y > limiar_chao and
            quadril_y > limiar_chao and
            joelho_y > limiar_chao
        ) or (
            abs(nariz_y - quadril_y) < tolerancia and
            abs(quadril_y - joelho_y) < tolerancia
        )

        rosto_visivel = nariz.visibility > 0.5
        possivel_queda_costas = not rosto_visivel and quadril_y > limiar_chao and joelho_y > limiar_chao

        if deitado or possivel_queda_costas:
            if tempo_inicio_queda is None:
                tempo_inicio_queda = time.time()
            elif time.time() - tempo_inicio_queda >= tempo_queda_confirmada:
                nova_queda_confirmada = True
        else:
            tempo_inicio_queda = None

    # Envia sinal ao Arduino e conta quedas
    if nova_queda_confirmada and not queda_confirmada:
        queda_confirmada = True
        contador_quedas += 1 
        arduino.write(b'queda\n')
        print("Enviado: queda")

    elif not nova_queda_confirmada and queda_confirmada:
        queda_confirmada = False
        arduino.write(b'ok\n')
        print("Enviado: ok")

    # === Exibe informações na tela ===
    if queda_confirmada:
        cv2.putText(frame, "QUEDA DETECTADA!", (10, 100), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0, 0, 255), 3)
    elif nova_queda_confirmada:
        cv2.putText(frame, "Verificando queda...", (10, 100), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0, 165, 255), 2)

    # Mostra o número total de quedas
    cv2.putText(frame, f"Quedas: {contador_quedas}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX,
                1, (255, 255, 0), 2)

    # Mostra o frame com os dados
    cv2.imshow("Detecção de Quedas - MediaPipe", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# === Finaliza a aplicação ===
cap.release()
arduino.close()
cv2.destroyAllWindows()