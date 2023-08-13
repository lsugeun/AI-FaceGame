import os
import random
from flask import Flask, render_template, Response
import cv2
from cvzone.FaceMeshModule import FaceMeshDetector
import cvzone
import mysql.connector
from flask import render_template

app = Flask(__name__)

cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)

detector = FaceMeshDetector(maxFaces=2)
idList = [0, 17, 78, 292]

folderEatable = 'Objects/eatable'
listEatable = os.listdir(folderEatable)
eatables = []
for obj in listEatable:
    eatables.append(cv2.imread(f'{folderEatable}/{obj}', cv2.IMREAD_UNCHANGED))

folderNonEatable = 'Objects/noneatable'
listNonEatable = os.listdir(folderNonEatable)
nonEatables = []
for obj in listNonEatable:
    nonEatables.append(cv2.imread(f'{folderNonEatable}/{obj}', cv2.IMREAD_UNCHANGED))

currentObject = eatables[0]
pos = [300, 0]
speed = 5
count = 0
isEatable = True
gameOver = False
gamePaused = False

# MySQL 서버에 연결
cnx = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="facegame"
)

# 랭킹 정보를 추가하는 함수
def add_ranking(name, score):
    cursor = cnx.cursor()
    query = "INSERT INTO ranking (name, score) VALUES (%s, %s)"
    values = (name, score)
    cursor.execute(query, values)
    cnx.commit()
    cursor.close()

# 랭킹 정보를 조회하는 함수
def get_ranking():
    cursor = cnx.cursor()
    query = "SELECT * FROM ranking ORDER BY score DESC"
    cursor.execute(query)
    ranking = cursor.fetchall()
    cursor.close()
    return ranking

def resetObject():
    global currentObject, isEatable
    pos[0] = random.randint(100, 1180)
    pos[1] = 0
    randNo = random.randint(0, 2)
    if randNo == 0:
        currentObject = nonEatables[random.randint(0, 3)]
        isEatable = False
    else:
        currentObject = eatables[random.randint(0, 3)]
        isEatable = True

    return currentObject

def generate_frames():
    global gameOver, count, currentObject, pos, isEatable, gamePaused

    while True:
        success, img = cap.read()
        img = cv2.flip(img, 1)  # 이미지 좌우 반전

        if not gamePaused and gameOver is False:
            img, faces = detector.findFaceMesh(img, draw=False)

            img = cvzone.overlayPNG(img, currentObject, pos)
            pos[1] += speed

            if pos[1] > 520:
                currentObject = resetObject()

            if faces:
                face = faces[0]

                up = face[idList[0]]
                down = face[idList[1]]

                for id in idList:
                    cv2.circle(img, face[id], 5, (255, 0, 255), 5)
                cv2.line(img, up, down, (0, 255, 0), 3)
                cv2.line(img, face[idList[2]], face[idList[3]], (0, 255, 0), 3)

                upDown, _ = detector.findDistance(face[idList[0]], face[idList[1]])
                leftRight, _ = detector.findDistance(face[idList[2]], face[idList[3]])

                cx, cy = (up[0] + down[0]) // 2, (up[1] + down[1]) // 2
                cv2.line(img, (cx, cy), (pos[0] + 50, pos[1] + 50), (0, 255, 0), 3)
                distMouthObject, _ = detector.findDistance((cx, cy), (pos[0] + 50, pos[1] + 50))
                print(distMouthObject)

                ratio = int((upDown / leftRight) * 100)
                if ratio > 60:
                    mouthStatus = "Open"
                else:
                    mouthStatus = "Closed"
                cv2.putText(img, mouthStatus, (50, 50), cv2.FONT_HERSHEY_COMPLEX, 2, (255, 0, 255), 2)

                if distMouthObject < 100 and ratio > 60:
                    if isEatable:
                        currentObject = resetObject()
                        count += 1
                    else:
                        gameOver = True
                        # 게임 오버 시, 플레이어의 이름과 점수를 랭킹에 추가
                        name = "Player111"  # 플레이어의 이름을 설정하거나 입력 받을 수 있습니다.
                        add_ranking(name, count)

            cv2.putText(img, str(count), (1100, 50), cv2.FONT_HERSHEY_COMPLEX, 2, (255, 0, 255), 5)
        else:
            cv2.putText(img, "Game Over", (300, 400), cv2.FONT_HERSHEY_PLAIN, 7, (255, 0, 255), 10)

        ret, buffer = cv2.imencode('.jpg', img)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/reset_game', methods=['POST'])
def reset_game():
    global count, gamePaused, gameOver
    count = 0
    resetObject()
    gameOver = False
    gamePaused = False
    currentObject = eatables[0]
    pos = [300, 0]
    return "Game reset"

@app.route('/pause_game', methods=['POST'])
def pause_game():
    global gamePaused
    gamePaused = not gamePaused
    return "Game paused"

@app.route('/ranking')
def ranking():
    # 랭킹 조회 함수 호출하여 랭킹 리스트를 가져옴
    ranking_list = get_ranking()

    # 랭킹 데이터를 순위, 플레이어 이름, 스코어로 구성된 리스트로 변환
    ranking_data = [(index + 1  , data[1], data[2]) for index, data in enumerate(ranking_list)]

    return render_template('ranking.html', ranking=ranking_data)



@app.route('/ranking')
def show_ranking():
    # 랭킹 데이터를 가져오는 로직을 추가합니다.
    ranking_data = get_ranking_data()  # 적절한 랭킹 데이터 가져오기 함수를 호출하세요.

    return render_template('ranking.html', ranking_data=ranking_data)


if __name__ == '__main__':
    app.run(debug=True)
