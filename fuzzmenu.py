import tkinter as tk
import argparse
import pyautogui
import configparser
import json
import os
from functools import partial
from xdg.IconTheme import getIconPath
from xdg.BaseDirectory import xdg_config_home
from PIL import Image, ImageTk

parser = argparse.ArgumentParser(
    description="'lightweight' application launcher")

parser.add_argument("-x", type=int, default=-1,
                    help="uses mouse x if not defined")
parser.add_argument("-y", type=int, default=-1,
                    help="uses mouse y if not defined")
parser.add_argument("-g", "--geometry", type=str, default=None,
                    help="window geometry in the format of 'widthxheight+x+y'")
parser.add_argument("-ww", "--width", type=int, default=400)
parser.add_argument("-wh", "--height", type=int, default=500)
parser.add_argument("-c", "--categories", type=str,
                    default="Favorites,All Applications,,Utility,Development,Game,Graphics,Network,Multimedia:Audio:Video,Office,Settings,System:Filesystem",
                    help="categories to show in list")
parser.add_argument("-dc", "--default-category", type=str, default="Favorites",
                    help="category to start up to")
parser.add_argument("-f", "--quit-no-focus", action='store_true', default=False,
                    help="close fuzzmenu when switch windows")

args = parser.parse_args()


class VerticalScrolledFrame:
    def __init__(self, master, **kwargs):
        width = kwargs.pop('width', None)
        height = kwargs.pop('height', None)
        bg = kwargs.pop('bg', kwargs.pop('background', None))
        self.outer = tk.Frame(master, **kwargs)

        self.vsb = tk.Scrollbar(self.outer, orient=tk.VERTICAL)
        self.vsb.pack(fill=tk.Y, side=tk.RIGHT)
        self.canvas = tk.Canvas(
            self.outer, highlightthickness=0, width=width, height=height, bg=bg)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas['yscrollcommand'] = self.vsb.set
        # mouse scroll does not seem to work with just "bind"; You have
        # to use "bind_all". Therefore to use multiple windows you have
        # to bind_all in the current widget
        self.canvas.bind("<Enter>", self._bind_mouse)
        self.canvas.bind("<Leave>", self._unbind_mouse)
        self.vsb['command'] = self.canvas.yview

        self.inner = tk.Frame(self.canvas, bg=bg)
        # pack the inner Frame into the Canvas with the topleft corner 4 pixels offset
        self.canvas.create_window(4, 4, window=self.inner, anchor='nw')
        self.inner.bind("<Configure>", self._on_frame_configure)

        self.outer_attr = set(dir(tk.Widget))

    def empty(self):
        for w in self.inner.winfo_children():
            w.destroy()

    def __getattr__(self, item):
        if item in self.outer_attr:
            # geometry attributes etc (eg pack, destroy, tkraise) are passed on to self.outer
            return getattr(self.outer, item)
        else:
            # all other attributes (_w, children, etc) are passed to self.inner
            return getattr(self.inner, item)

    def _on_frame_configure(self, event=None):
        _x1, _y1, x2, y2 = self.canvas.bbox("all")
        height = self.canvas.winfo_height()
        self.canvas.config(scrollregion=(0, 0, x2, max(y2, height)))

    def _bind_mouse(self, event=None):
        self.canvas.bind_all("<4>", self._on_mousewheel)
        self.canvas.bind_all("<5>", self._on_mousewheel)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mouse(self, event=None):
        self.canvas.unbind_all("<4>")
        self.canvas.unbind_all("<5>")
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        """Linux uses event.num; Windows / Mac uses event.delta"""
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")

    def __str__(self):
        return str(self.outer)


class FuzzMenu(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.applications = []
        self.curapps = []
        self.curcategory = ""
        self.pack()

        # reloads apps from disk (saves favorites)
        self.master.bind("<Control-r>", lambda x: self.createAppDb())

        # clears all data including favorites
        self.master.bind("<Control-f>", lambda x: self.flushAppDb())

        self.search_bar_str = tk.StringVar(value="Search Applications")
        self.search_bar_str.trace(
            "w", lambda name, index, mode, sv=self.search_bar_str: self.searchEdit(sv))
        self.search_bar = tk.Entry(
            self.master, textvariable=self.search_bar_str)
        self.search_bar.bind("<FocusIn>", self.clickSearchBar)
        self.search_bar.pack()
        self.search_bar.place(x=0, y=0, w=args.width, h=20)

        self.categories_frame = tk.Frame(
            width=min(args.width / 3, 100), height=args.height - 20, highlightthickness=1)
        self.application_frame = VerticalScrolledFrame(  # only created to hold the scrollbar
            master=self.master,
            width=(args.width - min(args.width / 3, 100)), height=args.height - 20)

        self.application_frame.pack(fill="both", expand=True)

        # self.printwidgetinfo(self.application_frame)

        self.application_frame.place(
            x=(min(args.width / 3, 100)), y=20,
            width=(args.width - min(args.width / 3, 100)), height=(args.height - 20))

        self.categories_frame.pack()
        self.categories_frame.place(x=0, y=20)

        # create category buttons
        caty = 0
        for cat in args.categories.split(","):
            if cat == "":
                caty += 30
            else:
                firstcat = cat.split(":")[0]
                catbtn = tk.Button(self.categories_frame, text=firstcat,
                                   padx=0, command=partial(self.openCategory, cat))
                catbtn.pack(in_=self.categories_frame)
                catbtn.place(x=0, y=caty, width=(min(args.width / 3, 100)))
                caty += 30

        if os.path.isfile(xdg_config_home + "/fuzzmenu/apps.json"):
            print("loading app.json")
            self.loadAppDb()
        else:
            print("creating app.json")
            self.createAppDb()

        self.openCategory(args.default_category)

    def clickSearchBar(self, event):
        self.search_bar.delete(0, 'end')

    def searchEdit(self, search):
        print("searching: " + search.get())
        specialapps = []
        normalapps = []

        for app in self.applications:
            if search.get().lower() in app["Name"].lower():
                if app["favorite"]:
                    specialapps.append(app)
                else:
                    normalapps.append(app)

        self.curapps = []
        for sapp in specialapps:
            self.curapps.append(sapp)
        for napp in normalapps:
            self.curapps.append(napp)

        self.updateAppView()

    def flushAppDb(self):
        self.applications = []
        self.createAppDb()
        self.openCategory("All Applications")

    def loadAppDb(self):
        with open(xdg_config_home + "/fuzzmenu/apps.json", "r") as o:
            self.applications = json.loads(o.read())

    def createAppDb(self):
        existingfavorites = []
        if not self.applications == []:
            for app in self.applications:
                if app["favorite"]:
                    existingfavorites.append(app["filename"])

        self.applications = []

        for file in os.listdir("/usr/share/applications/"):
            if ".desktop" in file:
                print(file)
                config = configparser.ConfigParser(
                    strict=False, interpolation=None)
                config.read("/usr/share/applications/" + file)
                # print(list(config["Desktop Entry"].keys()))
                if config["Desktop Entry"]["Type"] == "Application":
                    appconfig = {}

                    appconfig["filename"] = file

                    if appconfig["filename"] in existingfavorites:
                        appconfig["favorite"] = True
                    else:
                        appconfig["favorite"] = False

                    if "Name" in config["Desktop Entry"].keys():
                        appconfig["Name"] = config["Desktop Entry"]["Name"]
                    else:
                        appconfig["Name"] = ""

                    if "Categories" in config["Desktop Entry"].keys():
                        appconfig["Categories"] = config["Desktop Entry"]["Categories"]
                    else:
                        appconfig["Categories"] = ""

                    if "Exec" in config["Desktop Entry"].keys():
                        appconfig["Exec"] = config["Desktop Entry"]["Exec"]
                    else:
                        appconfig["Exec"] = ""

                    if "Icon" in config["Desktop Entry"].keys():
                        appconfig["Icon"] = config["Desktop Entry"]["Icon"]
                        appconfig["IconPath"] = getIconPath(
                            appconfig["Icon"], 48)
                    else:
                        appconfig["Icon"] = ""
                        appconfig["IconPath"] = None

                    if "Comment" in config["Desktop Entry"].keys():
                        appconfig["Comment"] = config["Desktop Entry"]["Comment"]
                    else:
                        appconfig["Comment"] = ""

                    self.applications.append(appconfig)
        self.applications = sorted(self.applications, key=lambda x: x["Name"])

        os.makedirs(os.path.dirname(
            xdg_config_home + "/fuzzmenu/"), exist_ok=True)

        with open(xdg_config_home + "/fuzzmenu/apps.json", "w") as o:
            o.write(json.dumps(self.applications))

    def openCategory(self, cat):
        print("opening category: '" + cat + "'")
        self.curapps = []
        self.curcategory = cat

        if cat == "All Applications":
            for app in self.applications:
                self.curapps.append(app)
        elif cat == "Favorites":
            for app in self.applications:
                if app["favorite"]:
                    self.curapps.append(app)
        else:
            for app in self.applications:
                for cats in cat.split(":"):
                    if cats in app["Categories"].split(";"):
                        self.curapps.append(app)

        self.updateAppView()

    def openApp(self, app, evt):
        print("opening: " + app["Name"])
        os.system(app["Exec"] + " &")

    def toggleFavoriteApp(self, app, evt):
        print("toggling favorite on: " + app["Name"] + " to: ", end="")

        for sapp in self.applications:
            if sapp["filename"] == app["filename"]:
                sapp["favorite"] = not sapp["favorite"]
                print(sapp["favorite"])

        if self.curcategory == "Favorites":
            self.openCategory(self.curcategory)

        os.makedirs(os.path.dirname(
            xdg_config_home + "/fuzzmenu/"), exist_ok=True)

        with open(xdg_config_home + "/fuzzmenu/apps.json", "w") as o:
            o.write(json.dumps(self.applications))

    def updateAppView(self):
        appnum = 0
        self.application_frame.empty()
        self.application_frame._on_frame_configure()

        for app in self.curapps:
            appframe = tk.Frame(self.application_frame,
                                width=((args.width - min(args.width / 3, 100)) - 20), height=40,
                                highlightthickness=1)

            appname = tk.Label(appframe, text=app["Name"])
            appname.place(x=40, y=2)
            appcom = tk.Label(appframe, text=app["Comment"])
            appcom.place(x=40, y=19)

            iconpath = app["IconPath"]
            if not iconpath == None and not ".svg" in iconpath:
                rawimg = Image.open(iconpath)
                rawimg = rawimg.resize((40, 40), Image.ANTIALIAS)
                appframe.tkphoto = tkphoto = ImageTk.PhotoImage(rawimg)
                imgcanvas = tk.Canvas(appframe, width=40, height=40, bg="gray")
                imgcanvas.pack()
                imgcanvas.create_image(0, 0, image=tkphoto, anchor="nw")
                imgcanvas.place(x=0, y=0)
                imgcanvas.bind("<Button-1>", partial(self.openApp, app))

            appframe.bind("<Button-1>", partial(self.openApp, app))
            appname.bind("<Button-1>", partial(self.openApp, app))
            appcom.bind("<Button-1>", partial(self.openApp, app))

            appframe.bind("<Button-2>", partial(self.toggleFavoriteApp, app))
            appname.bind("<Button-2>", partial(self.toggleFavoriteApp, app))
            appcom.bind("<Button-2>", partial(self.toggleFavoriteApp, app))

            appframe.grid(column=0, row=appnum)
            appnum += 1

    def printwidgetinfo(self, w):
        print("frame inner position: x=" + str(w.winfo_x()) +
              " y=" + str(w.winfo_y()) + " w=" + str(w.winfo_width()) +
              " h=" + str(w.winfo_height()))


root = tk.Tk()
root.title("FuzzMenu")
root.resizable(False, False)
# root.overrideredirect(1)
root.bind("<Control-q>", lambda x: root.quit())
if args.quit_no_focus:
    root.bind("<FocusOut>", lambda x: root.quit())

if args.x == -1:
    args.x = pyautogui.position()[0]
if args.y == -1:
    args.y = pyautogui.position()[1]

if not args.geometry == None:
    root.wm_geometry(args.geometry)
else:
    root.wm_geometry(str(args.width) + "x" + str(args.height) +
                     "+" + str(args.x) + "+" + str(args.y))

app = FuzzMenu(master=root)
app.mainloop()
