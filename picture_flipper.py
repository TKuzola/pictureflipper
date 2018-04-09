"""
Created on Jan 10, 2018

@author: Tony Kuzola
"""
import random
import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import json
from PIL import ImageTk, Image, ExifTags



class RightClickMenu(tk.Frame):  # pylint: disable=too-many-ancestors
    """Class defining popup menu

        Creates popup menu with pause, file, and boss options
    """
    gui_instance = None

    def __init__(self, parent, instance):
        self.master = parent
        tk.Frame.__init__(self, self.master)
        self.right_click_menu = None
        self.gui_instance = instance
        self.create_widgets()

    def create_widgets(self):
        """Sets up widgets, only one action in this case
        """
        self.create_right_click_menu()

    def create_right_click_menu(self):
        """Builds right click menu
        """
        self.right_click_menu = tk.Menu(self.master, tearoff=0, relief='sunken')
        self.right_click_menu.add_command(label="Pause", command=self.pause)
        self.right_click_menu.add_command(label="Resume", command=self.resume, state=tk.DISABLED)
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(label="Boss", command=self.boss)
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(label="File name", command=self.file_name)

    def popup_text(self, event):
        """Handler for right click action
        """
        #print("right click")
        self.right_click_menu.post(event.x_root, event.y_root)

    def pause(self):
        """Keeps the file name of image being displayed from changing
        """
        #print("Pause")
        self.right_click_menu.entryconfigure(0, state=tk.DISABLED)
        self.right_click_menu.entryconfigure(1, state=tk.ACTIVE)
        self.gui_instance.pause()

    def resume(self):
        """Allows file name of image being displayed to change
        """
        #print("resume")
        self.right_click_menu.entryconfigure(1, state=tk.DISABLED)
        self.right_click_menu.entryconfigure(0, state=tk.ACTIVE)
        self.gui_instance.resume()

    def boss(self):
        """Changes file to be displayed to boss image and pauses
        """
        #print("Boss")
        self.pause()
        self.gui_instance.boss()

    def file_name(self):
        """Displays current file name and path
        """
        #print(self.gui_instance.get_cur_filename())
        messagebox.showinfo("Filename", self.gui_instance.get_cur_filename())


def get_file_list(directory, extension):
    """Returns target files

       Returns a list of files from the directory that match the extension
       Takes a directory and an extension type as parameters
    """

    files_to_show_list = []
    for dir_name, dummy_sub_dir_list, file_list in os.walk(directory):
        for fname in file_list:
            cur_file = os.path.join(dir_name, fname)
            if Path(cur_file).suffix == extension:
                files_to_show_list.append(cur_file)

    return files_to_show_list


def size_image_to_window(image_path, window_width, window_height):
    """Resize image with or height to fit window

       Returns a copy of the image with the with or height sized to window
       Takes a image file name, window width and window height
    """
    orientation = None
    img = Image.open(image_path)
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        exif = dict(img._getexif().items())   # pylint: disable=W0212

        if exif[orientation] == 3:
            print("rotate 180")
            img = img.rotate(180, expand=True)
        elif exif[orientation] == 6:
            print("rotate 270")
            img = img.rotate(270, expand=True)
        elif exif[orientation] == 8:
            print("rotate 90")
            img = img.rotate(90, expand=True)

    except (AttributeError, KeyError, IndexError):
        # cases: image don't have getexif
        pass
    [image_size_width, image_size_height] = img.size

    # print(image_size_width)
    # print(image_size_height)

    aspect_ratio = image_size_width / image_size_height

    if aspect_ratio > 1:
        new_image_size_width = window_width
        scale_ratio = new_image_size_width / image_size_width
        new_image_size_height = int(image_size_height * scale_ratio)
    else:
        new_image_size_height = window_height
        scale_ratio = new_image_size_height / image_size_height
        new_image_size_width = int(image_size_width * scale_ratio)

    # print(new_image_size_width)
    # print(new_image_size_height)

    img = img.resize((new_image_size_width, new_image_size_height), Image.ANTIALIAS)

    return ImageTk.PhotoImage(img)


class PictureFlipperGUI:
    """Main UI class

       Creates main window and updates the displayed picture in the window
       with a random file chosen from the list every x seconds
    """

    display_list = []
    directory_list = []
    extension_list = []
    current_window_width = 400
    current_window_height = 300
    current_picture = None
    main_panel = None
    init = True
    delay = 6000
    picture_file = None
    paused = False
    boss_picture = None

    def __init__(self, master):
        self.master = master

        master.geometry('{}x{}'.format(self.current_window_width, self.current_window_height))
        master.configure(background='grey')
        self.popup = None
        try:
            with open('picture_flipper_config.json', 'r') as json_config_file:
                config = json.load(json_config_file)
        except OSError as file_open_exception:
            print("Failed to open picture_flipper_config.json", file_open_exception)
            sys.exit(1)

        try:
            self.directory_list = config['PICTURES']['DIRECTORIES'].split(',')
            self.extension_list = config['PICTURES']['EXTENSIONS'].split(',')
            if config['PICTURES']['DELAY'] is not None:
                self.delay = config['PICTURES']['DELAY']
            if config['PICTURES']['TITLE'] is None:
                master.title("Hi!")
            else:
                master.title(config['PICTURES']['TITLE'])
            self.boss_picture = config['PICTURES']['BOSS_FILE']

        except KeyError as key_exception:
            print('KeyError while reading configuration file for key "%s"' % str(key_exception))
            sys.exit(1)

        except IndexError as index_exception:
            print('IndexError while reading configuration file - reason "%s"'
                  % str(index_exception))
            sys.exit(1)

        # Create the list of picture file names
        for directory in self.directory_list:
            for extension in self.extension_list:
                print(directory, extension)
                self.display_list = self.display_list + get_file_list(directory, extension)
        self.update_pic()

    def update_pic(self):
        """Refreshes the UI with next picture

           Updates the displayed picture in the window with a random file chosen from the list
           every x seconds
        """
        if self.paused is False:
            self.picture_file = random.choice(self.display_list)

        if self.init:
            self.current_picture = size_image_to_window(self.picture_file,
                                                        self.current_window_width,
                                                        self.current_window_height)
            self.main_panel = tk.Label(self.master, image=self.current_picture)
            self.popup = RightClickMenu(self.master, self)
            self.main_panel.bind("<Button-3>", self.popup.popup_text)
            self.main_panel.pack(side="bottom", fill="both", expand="yes")
            self.init = False
        else:
            self.current_picture = size_image_to_window(self.picture_file,
                                                        self.current_window_width,
                                                        self.current_window_height)
            self.current_window_width = self.master.winfo_width()
            self.current_window_height = self.master.winfo_height()

            self.main_panel.configure(image=self.current_picture)
            self.main_panel.image = self.current_picture

        self.master.after(self.delay, self.update_pic)

    def get_cur_filename(self):
        """Returns the current file name as a string

        """
        return self.picture_file

    def pause(self):
        """Keeps the picture from changing

           This function freeze the current picture file name and disables the pause
           popup menu selection while enabling the resume menu selection
        """
        self.paused = True

    def resume(self):
        """Undo of pause function

           This function unfreezes the current picture file name and disables the resume
           popup menu selection while enabling the pause menu selection
        """
        self.paused = False

    def boss(self):
        """Sets current picture to boss picture and calls update
        """
        self.picture_file = self.boss_picture
        self.update_pic()


SOLO_WINDOW = tk.Tk()
MY_GUI = PictureFlipperGUI(SOLO_WINDOW)
SOLO_WINDOW.mainloop()
