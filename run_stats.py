import tcx_pb2
import glob


def allTrackPoints(activity):
    all_tp = []
    for l in activity.lap:
        for t in l.track:
            all_tp.extend(t.trackpoint)

    return list(filter(lambda tp: tp.sensorPresent == True, all_tp))


def distanceBetween(tp1, tp2):
    return tp2.distanceMeters - tp1.distanceMeters


def timeBetween(tp1, tp2):
    return tp2.time - tp1.time


def bestSpan(activity, distance=400):
    all_tp = allTrackPoints(activity)
    span = [0, 1]
    best_time = -1
    if len(all_tp) < 1:
        return best_time
    if distanceBetween(all_tp[0], all_tp[-1]) < distance:
        return best_time
    while True:
        # increase the second index until the distance is larger than
        # distance
        while distanceBetween(all_tp[span[0]], all_tp[span[1]]) < distance:
            if span[1] < len(all_tp)-2:
                span[1] = span[1] + 1
            else:
                return best_time

        actual_distance = distanceBetween(all_tp[span[0]], all_tp[span[1]])
        time = timeBetween(all_tp[span[0]],
                           all_tp[span[1]]) * (distance/actual_distance)
        best_time = time if (
            time < best_time or best_time == -1) else best_time

        span[0] = span[0] + 1


pb_files = glob.glob('./pbdata/*.pb')
best5k = 100000000
for file_name in pb_files:
    tcd = tcx_pb2.TrainingCenterDatabase()

    # Read the existing address book.
    f = open(file_name, "rb")
    tcd.ParseFromString(f.read())
    f.close()

    if (tcd.activities.activity[0].sport != 'Running'):
        continue

    act5ktime = bestSpan(tcd.activities.activity[0], 5000)
    if (act5ktime != -1 and act5ktime < best5k):
        best5k = act5ktime
        print(file_name)
        print("New best for 5K: {}".format(best5k))
