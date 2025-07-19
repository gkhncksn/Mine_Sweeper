#!/usr/bin/env python3

# Copyright (c) 2016 Akuli
# ... (lisans kısmı aynı kalır)

import collections
import functools
import random
import tkinter as tk
from tkinter import messagebox
import webbrowser
from PIL import Image, ImageTk
import os
import time

# Core
# ~~~~

class Square:

    def __init__(self, opened=False, mine=False, flagged=False):
        self.opened = opened
        self.mine = mine
        self.flagged = flagged

    def __repr__(self):
        return ('<%s opened=%r mine=%r flagged=%r>'
                % (type(self).__name__, self.opened,
                   self.mine, self.flagged))


class Game:
    """One game that ends in a win or a gameover."""

    def __init__(self, width=9, height=9, mines=10):
        self.width = width
        self.height = height
        self.mines = mines
        self.remaining_mines = mines
        all_coords = [(x, y) for x in range(width) for y in range(height)]
        mine_coords = random.sample(all_coords, mines)
        self._squares = {coords: Square() for coords in all_coords}
        for coords in mine_coords:
            self[coords].mine = True

    def __getitem__(self, coords):
        return self._squares[coords]

    def toggle_flag(self, coords):
        if not self[coords].opened:
            if self[coords].flagged:
                self[coords].flagged = False
                self.remaining_mines += 1
            else:
                self[coords].flagged = True
                self.remaining_mines -= 1

    def open(self, coords):
        if not self[coords].flagged and not self[coords].opened:
            self[coords].opened = True
            if self.number_of_mines_around(coords) == 0:
                self.auto_open(coords)

    def auto_open(self, coords):
        for coords in self.coords_around(coords):
            if not self[coords].opened and not self[coords].flagged:
                self.open(coords)

    def coords_around(self, coords):
        centerx, centery = coords
        for xdiff in (-1, 0, 1):
            for ydiff in (-1, 0, 1):
                if xdiff == ydiff == 0:
                    # Center.
                    continue
                x = centerx + xdiff
                y = centery + ydiff
                if x in range(self.width) and y in range(self.height):
                    # The place is on the board, not beyond an edge.
                    yield x, y

    def mines_around(self, coords):
        for minecoords in self.coords_around(coords):
            if self[minecoords].mine:
                yield minecoords

    def number_of_mines_around(self, coords):
        result = 0
        for coords_around in self.mines_around(coords):
            result += 1
        return result

    def all_coords(self):
        return self._squares.keys()

    def explosion_coords(self):
        for coords in self.all_coords():
            if self[coords].mine and self[coords].opened:
                return coords
        return None

    def exploded(self):
        return self.explosion_coords() is not None

    def win(self):
        for coords in self.all_coords():
            if not (self[coords].mine or self[coords].opened):
                return False
        return not self.exploded()

    def over(self):
        return self.exploded() or self.win()


# Tkinter GUI
# ~~~~~~~~~~~

class PlayingArea(tk.Canvas):
    SCALE = 20
    NUMBER_COLORS = ['', 'blue', 'green', 'red', 'darkblue', 'darkred', 'teal', 'black', 'gray']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind('<ButtonRelease-1>', self._leftclick)
        self.bind('<ButtonRelease-3>', self._rightclick)
        self.game = None
        self.face_images = self._load_face_images()
        self.mine_images = self._load_mine_images()
        self.remaining_mines_var = None
        self.timer_var = None
        self.start_time = 0
        self.timer_id = None

    def _load_face_images(self):
        faces = {}
        for face in ['happy', 'oh', 'win', 'dead']:
            try:
                # Basit geometrik şekillerle yüz ifadeleri oluştur
                img = Image.new('RGBA', (26, 26), (192, 192, 192, 0))
                d = Image.Draw(img)
                
                if face == 'happy':
                    # Gülümseyen yüz
                    d.ellipse((2, 2, 24, 24), outline='black', width=2)
                    d.arc((6, 8, 10, 10), 0, 360, fill='black', width=2)  # Sol göz
                    d.arc((16, 8, 20, 10), 0, 360, fill='black', width=2)  # Sağ göz
                    d.arc((6, 12, 20, 20), 0, -180, fill='black', width=2)  # Ağız
                elif face == 'oh':
                    # Şaşkın yüz
                    d.ellipse((2, 2, 24, 24), outline='black', width=2)
                    d.ellipse((8, 8, 12, 12), fill='black')  # Sol göz
                    d.ellipse((16, 8, 20, 12), fill='black')  # Sağ göz
                    d.ellipse((10, 16, 18, 20), fill='black')  # Ağız
                elif face == 'win':
                    # Güneş gözlüklü yüz
                    d.ellipse((2, 2, 24, 24), outline='black', width=2)
                    d.rectangle((6, 8, 20, 14), fill='black')  # Gözlük
                    d.line((6, 11, 20, 11), fill='white', width=2)  # Gözlük camı
                    d.arc((6, 12, 20, 20), 0, -180, fill='black', width=2)  # Ağız
                elif face == 'dead':
                    # Ölü yüz
                    d.ellipse((2, 2, 24, 24), outline='black', width=2)
                    d.line((8, 8, 12, 12), fill='black', width=2)  # Sol göz çapraz
                    d.line((8, 12, 12, 8), fill='black', width=2)  # Sol göz çapraz
                    d.line((16, 8, 20, 12), fill='black', width=2)  # Sağ göz çapraz
                    d.line((16, 12, 20, 8), fill='black', width=2)  # Sağ göz çapraz
                    d.line((8, 20, 18, 20), fill='black', width=2)  # Ağız
                
                faces[face] = ImageTk.PhotoImage(img)
            except Exception:
                # Fallback: Renkli daireler
                faces[face] = {
                    'happy': 'yellow',
                    'oh': 'orange',
                    'win': 'gold',
                    'dead': 'red'
                }[face]
        return faces

    def _load_mine_images(self):
        images = {}
        for name in ['mine', 'flag', 'cross']:
            try:
                img = Image.new('RGBA', (self.SCALE-2, self.SCALE-2), (192, 192, 192, 0))
                d = Image.Draw(img)
                
                if name == 'mine':
                    # Mayın
                    d.ellipse((2, 2, self.SCALE-4, self.SCALE-4), fill='black')
                    d.line((self.SCALE//2, 4, self.SCALE//2, self.SCALE-4), fill='gray', width=2)
                    d.line((4, self.SCALE//2, self.SCALE-4, self.SCALE//2), fill='gray', width=2)
                    d.line((6, 6, self.SCALE-6, self.SCALE-6), fill='gray', width=1)
                    d.line((6, self.SCALE-6, self.SCALE-6, 6), fill='gray', width=1)
                elif name == 'flag':
                    # Bayrak
                    d.polygon([(4, 8), (4, 18), (16, 13)], fill='red')
                    d.line((4, 8, 4, self.SCALE-4), fill='black', width=2)
                elif name == 'cross':
                    # Çapraz işaret
                    d.line((4, 4, self.SCALE-4, self.SCALE-4), fill='red', width=2)
                    d.line((4, self.SCALE-4, self.SCALE-4, 4), fill='red', width=2)
                
                images[name] = ImageTk.PhotoImage(img)
            except Exception:
                # Fallback: Renkli semboller
                images[name] = {
                    'mine': 'black',
                    'flag': 'red',
                    'cross': 'red'
                }[name]
        return images

    def new_game(self, difficulty='Normal'):
        difficulties = {
            'Easy': (9, 9, 10),
            'Normal': (16, 16, 40),
            'Expert': (30, 16, 99)
        }
        width, height, mines = difficulties[difficulty]
        
        if self.game and self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
            
        self.game = Game(width, height, mines)
        self['width'] = self.SCALE * width
        self['height'] = self.SCALE * height
        
        self.remaining_mines_var.set(str(self.game.remaining_mines).zfill(3))
        self.timer_var.set('000')
        self.start_time = time.time()
        self.timer_id = self.after(1000, self.update_timer)
        
        self.update_face('happy')
        self.update()

    def update_timer(self):
        if self.game and not self.game.over():
            elapsed = int(time.time() - self.start_time)
            self.timer_var.set(str(min(elapsed, 999)).zfill(3))
            self.timer_id = self.after(1000, self.update_timer)

    def update_face(self, state):
        face_img = self.face_images[state]
        if isinstance(face_img, str):
            self.face_button.config(bg=face_img)
        else:
            self.face_button.config(image=face_img)

    def update(self):
        self.delete('all')
        if not self.game:
            return
            
        for coords in self.game.all_coords():
            self._draw_square(coords, self.game[coords])
        
        self.remaining_mines_var.set(str(self.game.remaining_mines).zfill(3))
        
        if self.game.win():
            if self.timer_id:
                self.after_cancel(self.timer_id)
                self.timer_id = None
            self.update_face('win')
            messagebox.showinfo("Minesweeper", "Tebrikler! Kazandınız.")
        elif self.game.exploded():
            if self.timer_id:
                self.after_cancel(self.timer_id)
                self.timer_id = None
            self.update_face('dead')
            messagebox.showinfo("Minesweeper", "Mayına bastınız! Kaybettiniz.")

    def _draw_square(self, coords, square):
        x, y = coords
        left = x * self.SCALE
        right = x * self.SCALE + self.SCALE
        top = y * self.SCALE
        bottom = y * self.SCALE + self.SCALE
        centerx = (left + right) // 2
        centery = (top + bottom) // 2

        # Klasik Minesweeper görünümü
        if square.opened:
            # Açılmış kare
            self.create_rectangle(left, top, right, bottom, fill='#d0d0d0', outline='gray')
            
            if square.mine:
                # Mayın
                mine_img = self.mine_images['mine']
                if isinstance(mine_img, str):
                    self.create_rectangle(left, top, right, bottom, fill='red' if coords == self.game.explosion_coords() else '#d0d0d0')
                    self.create_oval(centerx-6, centery-6, centerx+6, centery+6, fill='black')
                else:
                    self.create_image(centerx, centery, image=mine_img)
            else:
                # Mayın sayısı
                num = self.game.number_of_mines_around(coords)
                if num > 0:
                    color = self.NUMBER_COLORS[num]
                    self.create_text(centerx, centery, text=str(num), fill=color, font=('Helvetica', 10, 'bold'))
        else:
            # Kapalı kare (buton efekti)
            self.create_rectangle(left, top, right, bottom, fill='#c0c0c0', outline='white', width=1)
            self.create_rectangle(left+1, top+1, right-1, bottom-1, fill='#c0c0c0', outline='#808080', width=1)
            
            if square.flagged:
                # Bayraklı kare
                flag_img = self.mine_images['flag']
                if isinstance(flag_img, str):
                    points = [
                        centerx, centery-6,
                        centerx+8, centery-2,
                        centerx, centery+2
                    ]
                    self.create_polygon(points, fill='red', outline='black')
                    self.create_line(centerx, centery+2, centerx, centery+6, fill='black', width=2)
                else:
                    self.create_image(centerx, centery, image=flag_img)
                    
                # Yanlış bayraklama (oyun bittiğinde)
                if self.game.over() and not square.mine:
                    cross_img = self.mine_images['cross']
                    if isinstance(cross_img, str):
                        self.create_line(left+4, top+4, right-4, bottom-4, fill='red', width=2)
                        self.create_line(left+4, bottom-4, right-4, top+4, fill='red', width=2)
                    else:
                        self.create_image(centerx, centery, image=cross_img)

    def __click_handler(func):
        @functools.wraps(func)
        def inner(self, event):
            if not self.game or self.game.over():
                return
                
            x = event.x // self.SCALE
            y = event.y // self.SCALE

            if x in range(self.game.width) and y in range(self.game.height):
                if func.__name__ == '_leftclick':
                    self.update_face('oh')
                    self.after(200, lambda: self.update_face('happy') if not self.game.over() else None)
                result = func(self, (x, y))
                self.update()
            return result
        return inner

    @__click_handler
    def _leftclick(self, coords):
        self.game.open(coords)

    @__click_handler
    def _rightclick(self, coords):
        self.game.toggle_flag(coords)


def wikihow_howto():
    webbrowser.open('http://www.wikihow.com/Play-Minesweeper')


def about():
    messagebox.showinfo("Mayın Tarlası Hakkında",
                        "Bu oyun Python ve Tkinter kullanılarak geliştirilmiştir.\n\n"
                        "Orjinal Microsoft Minesweeper'e benzer bir deneyim sunmayı amaçlar.\n\n"
                        "Özellikler:\n"
                        "- Kolay, Normal, Uzman zorluk seviyeleri\n"
                        "- Kalan mayın sayacı\n"
                        "- Süre ölçer\n"
                        "- Klasik arayüz")


def main():
    root = tk.Tk()
    root.title("Mayın Tarlası")
    root.resizable(width=False, height=False)
    
    # Üst panel (sayaçlar ve yüz butonu)
    top_frame = tk.Frame(root, bg='#c0c0c0', padx=5, pady=5)
    top_frame.pack(fill='x')
    
    # Kalan mayın sayacı
    mine_frame = tk.Frame(top_frame, bg='black', padx=2, pady=2)
    mine_frame.pack(side='left')
    remaining_mines_var = tk.StringVar(value='000')
    mine_label = tk.Label(mine_frame, textvariable=remaining_mines_var, 
                          font=('Digital-7', 20), bg='black', fg='red', width=3)
    mine_label.pack()

    # Yüz butonu (reset)
    face_button = tk.Button(top_frame, text='😊', font=('Arial', 14), 
                           command=lambda: playingarea.new_game(difficulty.get()))
    face_button.pack(side='top', padx=20)

    # Zaman sayacı
    time_frame = tk.Frame(top_frame, bg='black', padx=2, pady=2)
    time_frame.pack(side='right')
    timer_var = tk.StringVar(value='000')
    time_label = tk.Label(time_frame, textvariable=timer_var, 
                         font=('Digital-7', 20), bg='black', fg='red', width=3)
    time_label.pack()

    # Oyun alanı
    playingarea = PlayingArea(root, bg='#c0c0c0')
    playingarea.pack(fill='both', expand=True, padx=5, pady=(0, 5))
    playingarea.remaining_mines_var = remaining_mines_var
    playingarea.timer_var = timer_var
    playingarea.face_button = face_button

    # Menü
    menubar = tk.Menu(root)
    root['menu'] = menubar

    # Oyun menüsü
    game_menu = tk.Menu(menubar, tearoff=False)
    difficulty = tk.StringVar(value='Normal')
    
    diff_menu = tk.Menu(game_menu, tearoff=False)
    diff_menu.add_radiobutton(label="Kolay (9x9, 10 mayın)", variable=difficulty, value='Easy',
                             command=lambda: playingarea.new_game('Easy'))
    diff_menu.add_radiobutton(label="Normal (16x16, 40 mayın)", variable=difficulty, value='Normal',
                             command=lambda: playingarea.new_game('Normal'))
    diff_menu.add_radiobutton(label="Uzman (30x16, 99 mayın)", variable=difficulty, value='Expert',
                             command=lambda: playingarea.new_game('Expert'))
    
    game_menu.add_cascade(label="Zorluk Seviyesi", menu=diff_menu)
    game_menu.add_command(label="Yeni Oyun", 
                         command=lambda: playingarea.new_game(difficulty.get()))
    game_menu.add_separator()
    game_menu.add_command(label="Çıkış", command=root.destroy)
    menubar.add_cascade(label="Oyun", menu=game_menu)

    # Yardım menüsü
    help_menu = tk.Menu(menubar, tearoff=False)
    help_menu.add_command(label="Nasıl Oynanır?", command=wikihow_howto)
    help_menu.add_command(label="Hakkında", command=about)
    menubar.add_cascade(label="Yardım", menu=help_menu)

    # İlk oyunu başlat
    playingarea.new_game('Normal')

    root.mainloop()


if __name__ == '__main__':
    main()
