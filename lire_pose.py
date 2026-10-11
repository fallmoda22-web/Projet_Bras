from robodk import robolink

RDK = robolink.Robolink()
robot = RDK.Item('ABB IRB 120-3/0.6', robolink.ITEM_TYPE_ROBOT)

if robot.Valid():
    print("Robot trouvé :", robot.Name())
    print("Pose XYZ (mm):", robot.Pose().Pos())
    print("Axes (deg):", robot.Joints().list())
else:
    print("Robot introuvable : vérifiez le nom dans l'arbre")