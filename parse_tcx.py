import xml.dom.minidom

dom = xml.dom.minidom.parse('./tcxdata/2019-05-28T11_45_53.000Z_3528649242.tcx')

class TrackPoint:
    distance = 0.0

    def __str__(self):
        return "Distance: {}".format(self.distance)

def handleTrackPoint(trackPointNode):
    trackPoint = TrackPoint()
    distanceMetersNode = trackPointNode.getElementsByTagName("DistanceMeters")[0]
    distanceText = distanceMetersNode.childNodes[0].nodeValue
    trackPoint.distance = float(distanceText)
    return trackPoint



tcd = dom.getElementsByTagName("TrainingCenterDatabase")[0]
for activities in tcd.childNodes:
    for activity in activities.childNodes:
        if activity.nodeName != "Activity":
            continue
        print(activity.attributes["Sport"].nodeValue)
        for activityChild in activity.childNodes:
            if (activityChild.nodeName != "Lap"):
                continue
            for lapChild in activityChild.childNodes:
                if (lapChild.nodeName != "Track"):
                    continue
                for trackChild in lapChild.childNodes:
                    if (trackChild.nodeName != "Trackpoint"):
                        continue
                    print(handleTrackPoint(trackChild))