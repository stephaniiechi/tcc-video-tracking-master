import cv2
import cv2.aruco as aruco

if __name__ == "__main__":

    aruco_dict = aruco.Dictionary_get(aruco.DICT_6X6_250)
    PIXELS = 500
    for markerId in range(0, 250):
        img = aruco.drawMarker(aruco_dict, markerId, PIXELS)
        cv2.imwrite("markers/marker_" + str(markerId) + ".jpg", img)
