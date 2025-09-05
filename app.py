import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import math
import threading
import main_v1 

class ModernGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        
        base = Path(__file__).parent
        png_path = base / "assets" / "icon16.png"   # fallback

        # Window configuration
        self.title("Mark Scraper 3000")
        
        try:
            if png_path.exists():
                self._icon_img = tk.PhotoImage(file=str(png_path))
                self.iconphoto(True, self._icon_img)
        except Exception:
            pass


        self.geometry("600x700")
        self.resizable(False, False)
        self.configure(bg='#0F1419')
        
        # Remove default window decorations for a more modern look
        self.attributes('-alpha', 0.98)

        # medicare categories
        self.medicare_categories = [
            "Physician",
            "Hospital",
            "Nursing Home",
            "Home Health",
            "Hospice",
            "Dialysis Facility",
            "Inpatient Rehabilitation",
            "Long Term Care" 
        ]
        
        # Color scheme
        self.colors = {
            'bg': '#0F1419',
            'card_bg': '#1A1F29',
            'accent': '#00D4FF',
            'accent_hover': '#0099CC',
            'text': '#FFFFFF',
            'text_secondary': '#8892B0',
            'success': '#00D4FF',
            'warning': '#FFB74D',
            'error': '#FF6B6B',
            'gradient_start': '#667EEA',
            'gradient_end': '#764BA2'
        }
        
        # Configure styles
        self._setup_styles()
        
        # Variables
        self.location_var = tk.StringVar()
        self.yellow_pages_keyword_search_var = tk.StringVar()
        self.google_maps_keyword_search_var = tk.StringVar()
        self.limit_var = tk.IntVar(value=50)
        self.radius_var = tk.StringVar(value="5")
        self.status_var = tk.StringVar(value="") 
        self.providers = {
            "YellowPages": tk.BooleanVar(value=False),
            "GoogleMaps": tk.BooleanVar(value=False),
        }
        self.yellow_pages_facilities = {
            "Hospital": tk.BooleanVar(value=False),
            "Pharmacy": tk.BooleanVar(value=False),
            "Clinic": tk.BooleanVar(value=False),
            "Diagnostic": tk.BooleanVar(value=False)
        }
        self.google_maps_facilities = {
            "Hospital": tk.BooleanVar(value=False),
            "Pharmacy": tk.BooleanVar(value=False),
            "Clinic": tk.BooleanVar(value=False),
            "Diagnostic": tk.BooleanVar(value=False)
        }
        self.selected_categories = {
            "Physician": tk.BooleanVar(value=False),
            "Hospital": tk.BooleanVar(value=False),
            "NursingHome": tk.BooleanVar(value=False),
            "HomeHealth": tk.BooleanVar(value=False),
            "Hospice": tk.BooleanVar(value=False),
            "DialysisFacility": tk.BooleanVar(value=False),
            "InpatientRehabilitation": tk.BooleanVar(value=False),
            "LongTermCare" : tk.BooleanVar(value=False),
        }
        
        # Animation variables
        self.animation_step = 0
        # self.animate_gradient()
        
        self._build_modern_ui()
        self._add_animations()
        
        # Center the window
        self._center_window()
    
    def _setup_styles(self):
        """Configure modern ttk styles"""
        style = ttk.Style()
        
        # Configure modern frame style
        style.configure('Modern.TFrame', 
                       background=self.colors['card_bg'],
                       borderwidth=0,
                       relief='flat')
        
        # Modern label style
        style.configure('Title.TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['text'],
                       font=('SF Pro Display', 24, 'bold'))
        
        style.configure('Subtitle.TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['text_secondary'],
                       font=('SF Pro Display', 12))
        
        style.configure('Modern.TLabel',
                       background=self.colors['card_bg'],
                       foreground=self.colors['text'],
                       font=('SF Pro Text', 11, 'bold'))
        
        # Modern entry style
        style.configure('Modern.TEntry',
                       borderwidth=0,
                       relief='flat',
                       fieldbackground='#2A3441',
                       foreground=self.colors['text'],
                       insertcolor=self.colors['accent'],
                       font=('SF Pro Text', 11))
        
        # Modern combobox style
        style.configure('Modern.TCombobox',
                       borderwidth=0,
                       relief='flat',
                       fieldbackground='#2A3441',
                       foreground=self.colors['text'],
                       font=('SF Pro Text', 11))
        
        # Modern checkbutton style
        style.configure('Modern.TCheckbutton',
                       background=self.colors['card_bg'],
                       foreground=self.colors['text'],
                       focuscolor='none',
                       font=('SF Pro Text', 10, 'bold'))
    
    def _build_modern_ui(self):
        """Build the modern UI with tighter vertical spacing and scrolling"""

        # ensure vars
        if not hasattr(self, "keyword_search_var"):
            self.keyword_search_var = tk.StringVar()
        if not hasattr(self, "is_searching"):
            self.is_searching = False
        if not hasattr(self, "status_var"):
            self.status_var = tk.StringVar(value="")

        # normalize medicare_categories
        if not hasattr(self, "medicare_categories"):
            self.medicare_categories = {}
        if isinstance(self.medicare_categories, (list, tuple, set)):
            self.medicare_categories = {name: tk.BooleanVar(value=False) for name in self.medicare_categories}
        elif isinstance(self.medicare_categories, dict):
            for k, v in list(self.medicare_categories.items()):
                if not isinstance(v, tk.BooleanVar):
                    self.medicare_categories[k] = tk.BooleanVar(value=bool(v))

        # ---------- HEADER (shorter) ----------
        header_frame = tk.Frame(self, bg=self.colors['bg'], height=90)
        header_frame.pack(fill='x', padx=0, pady=0)
        header_frame.pack_propagate(False)

        self.gradient_canvas = tk.Canvas(header_frame, height=90, bg=self.colors['bg'], highlightthickness=0)
        self.gradient_canvas.pack(fill='both', expand=True)

        title = tk.Label(header_frame, text="🏥 Mark Scraper 3000",
                        bg=self.colors['bg'], fg=self.colors['text'],
                        font=('SF Pro Display', 20, 'bold'))
        title.place(relx=0.5, rely=0.38, anchor='center')

        subtitle = tk.Label(header_frame, text="Find healthcare providers in your area",
                            bg=self.colors['bg'], fg=self.colors['text_secondary'],
                            font=('SF Pro Display', 10))
        subtitle.place(relx=0.5, rely=0.70, anchor='center')

        # ---------- SMART SCROLLABLE CONTENT AREA ----------
        # Create main container for scrollable area
        main_container = tk.Frame(self, bg=self.colors['bg'])
        main_container.pack(fill='both', expand=True, padx=16, pady=0)

        # Create canvas for scrolling (no visible scrollbar)
        canvas = tk.Canvas(main_container, bg=self.colors['bg'], highlightthickness=0)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg'])

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.pack(fill="both", expand=True)

        # Smart scrolling - only enable when content overflows
        def _check_scroll_needed():
            """Check if scrolling is needed and enable/disable accordingly"""
            canvas.update_idletasks()
            canvas_height = canvas.winfo_height()
            content_height = scrollable_frame.winfo_reqheight()
            
            if content_height > canvas_height:
                # Content overflows - enable scrolling
                canvas.configure(scrollregion=canvas.bbox("all"))
                canvas.bind('<Enter>', _bind_mousewheel)
                canvas.bind('<Leave>', _unbind_mousewheel)
            else:
                # Content fits - disable scrolling
                canvas.configure(scrollregion=(0, 0, 0, 0))
                canvas.unbind('<Enter>')
                canvas.unbind('<Leave>')
                _unbind_mousewheel(None)

        # Configure scrolling check
        scrollable_frame.bind("<Configure>", lambda e: _check_scroll_needed())
        canvas.bind('<Configure>', lambda e: [
            canvas.itemconfig(canvas.find_all()[0], width=e.width) if canvas.find_all() else None,
            _check_scroll_needed()
        ])

        # Bind mousewheel to canvas (works on Windows, macOS, Linux)
        def _on_mousewheel(event):
            # Only scroll if scrolling is enabled
            if canvas.cget('scrollregion') == '0 0 0 0':
                return
                
            # Handle different platforms
            if event.delta:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            else:
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")
        
        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows
            canvas.bind_all("<Button-4>", _on_mousewheel)    # Linux
            canvas.bind_all("<Button-5>", _on_mousewheel)    # Linux
        
        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
        
        # Initial check (will be called again after content is added)
        self.after(100, _check_scroll_needed)

        # Now use scrollable_frame as the content_frame
        content_frame = scrollable_frame

        # === Location & Search filters ===
        location_card = tk.Frame(content_frame, bg=self.colors['card_bg'], pady=8, padx=12)
        location_card.pack(fill='x', pady=(0, 4))
        self._add_shadow_effect(location_card)

        tk.Label(location_card, text="Location", bg=self.colors['card_bg'], fg=self.colors['text'],
                font=('SF Pro Text', 10, 'bold')).pack(anchor='w', pady=(0, 2))

        loc_row = tk.Frame(location_card, bg='#2A3441')
        loc_row.pack(fill='x', pady=(0, 2))
        location_entry = tk.Entry(loc_row, textvariable=self.location_var,
                                bg='#2A3441', fg=self.colors['text'],
                                borderwidth=0, relief='flat',
                                font=('SF Pro Text', 11),
                                insertbackground=self.colors['accent'])
        location_entry.pack(side='left', fill='x', expand=True, padx=10, pady=4)
        tk.Label(location_card, text="e.g., Los Angeles, CA 90210",
                bg=self.colors['card_bg'], fg=self.colors['text_secondary'],
                font=('SF Pro Text', 9)).pack(anchor='w', pady=(0, 2))
        
        
        ### RESULT LIMITER
        grid = tk.Frame(location_card, bg=self.colors['card_bg'])
        grid.pack(fill='x')
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        left = tk.Frame(grid, bg=self.colors['card_bg'])
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 6))
        tk.Label(left, text="Result Limit", bg=self.colors['card_bg'], fg=self.colors['text'],
                font=('SF Pro Text', 10, 'bold')).pack(anchor='w')
        limit_spinbox = tk.Spinbox(left, from_=1, to=100000, textvariable=self.limit_var,
                                bg='#2A3441', fg=self.colors['text'],
                                borderwidth=0, relief='flat',
                                buttonbackground=self.colors['accent'],
                                font=('SF Pro Text', 11), width=15)
        limit_spinbox.pack(anchor='w', pady=(4, 0), fill='x')

        
        ### SEARCH RADIUS
        right = tk.Frame(grid, bg=self.colors['card_bg'])
        right.grid(row=0, column=1, sticky='nsew', padx=(6, 0))
        tk.Label(right, text="Search Radius (miles)", bg=self.colors['card_bg'], fg=self.colors['text'],
                font=('SF Pro Text', 10, 'bold')).pack(anchor='w')
        self.radius_var.set("5")
        miles = [str(i) for i in range(5, 255, 5)]
        radius_combo = ttk.Combobox(right, values=miles, textvariable=self.radius_var,
                                    state="readonly", width=15, style='Modern.TCombobox')
        radius_combo.pack(anchor='w', pady=(4, 0), fill='x')
        
        
        # --- Yellow Pages section (tight) ---
        yellow_page_frame = tk.Frame(content_frame, bg=self.colors['bg'])
        yellow_page_frame.pack(fill='x', expand=False, padx=0, pady=(0, 2))   # was expand=True / bigger pady

        yellow_page_search_card = tk.Frame(yellow_page_frame, bg=self.colors['card_bg'], pady=4, padx=12)
        yellow_page_search_card.pack(fill='x', expand=False, pady=(0, 2))  
        self._add_shadow_effect(yellow_page_search_card)

        ### YELLOW PAGES HEADER ###
        tk.Label(yellow_page_search_card, text="Yellow Pages", bg=self.colors['card_bg'], fg=self.colors['text'],
                font=('SF Pro Text', 14, 'bold')).pack(anchor='center', pady=(0, 2))

        ### YELLOW PAGES SUBHEADING
        tk.Label(yellow_page_search_card, text="Search keyword", bg=self.colors['card_bg'], fg=self.colors['text'],
        font=('SF Pro Text', 10, 'bold')).pack(anchor='w', pady=(0, 2))

        yp_row = tk.Frame(yellow_page_search_card, bg='#2A3441')
        yp_row.pack(fill='x', pady=(0, 2))
        yp_keyword_entry = tk.Entry(yp_row, textvariable=self.yellow_pages_keyword_search_var,
                                bg='#2A3441', fg=self.colors['text'],
                                borderwidth=0, relief='flat',
                                font=('SF Pro Text', 11),
                                insertbackground=self.colors['accent'])
        yp_keyword_entry.pack(side='left', fill='x', expand=True, padx=10, pady=4)

        tk.Label(yellow_page_search_card, text="e.g., Doctors, Clinics, or Pharmacies...",
                bg=self.colors['card_bg'], fg=self.colors['text_secondary'],
                font=('SF Pro Text', 9)).pack(anchor='w', pady=(0, 2))

        ### RADIO BUTTONS
        # Initialize the keyword search var with empty value initially
        if not hasattr(self, "yellow_pages_keyword_search_var"):
            self.yellow_pages_keyword_search_var = tk.StringVar(value="")

        # Create a separate variable for radio button selection
        if not hasattr(self, "yellow_pages_radio_var"):
            self.yellow_pages_radio_var = tk.StringVar(value="NONE_SELECTED")  # Use a value that doesn't match any radio
            
        if "YellowPages" not in self.providers:
            self.providers["YellowPages"] = tk.BooleanVar(value=False)
            
        def _sync_yp_provider(*_):
            """Enable Yellow Pages source whenever there's a non-empty keyword."""
            kw = self.yellow_pages_keyword_search_var.get().strip()
            self.providers["YellowPages"].set(bool(kw))

        # Update on any change to the keyword var
        self.yellow_pages_keyword_search_var.trace_add("write", _sync_yp_provider)

        def on_radio_select():
            """Update the keyword search field when radio button is selected"""
            selected = self.yellow_pages_radio_var.get()
            if selected and selected != "NONE_SELECTED":
                self.yellow_pages_keyword_search_var.set(selected)
            _sync_yp_provider()

        rb_row = tk.Frame(yellow_page_search_card, bg=self.colors['card_bg'])
        rb_row.pack(fill='x', pady=(2, 2))

        # a centered strip that holds the radios
        rb_strip = tk.Frame(rb_row, bg=self.colors['card_bg'])
        rb_strip.pack(anchor='w')
        
        _sync_yp_provider()

        for name, var in self.yellow_pages_facilities.items():
            tk.Radiobutton(
                rb_strip,
                text=name,
                variable=self.yellow_pages_radio_var,  # Use the radio variable
                value=name,  # Use the name as the value
                command=on_radio_select,  # Add callback function
                bg=self.colors['card_bg'],
                fg=self.colors['text'],
                activebackground=self.colors['card_bg'],
                activeforeground=self.colors['text'],
                selectcolor='#2A3441',   # inner circle color
                highlightthickness=0,
                font=('SF Pro Text', 10)
            ).pack(side='left', padx=10, pady=2)

        #### GOOGLE MAPS SECTION ###
        google_maps_frame = tk.Frame(content_frame, bg=self.colors['bg'])
        google_maps_frame.pack(fill='x', expand=False, padx=0, pady=(0, 2))   # was expand=True / bigger pady

        google_maps_search_card = tk.Frame(google_maps_frame, bg=self.colors['card_bg'], pady=4, padx=12)
        google_maps_search_card.pack(fill='x', expand=False, pady=(0, 2))
        self._add_shadow_effect(google_maps_search_card)

        ### GOOGLE MAPS HEADER ###
        tk.Label(google_maps_search_card, text="Google Maps", bg=self.colors['card_bg'], fg=self.colors['text'],
                font=('SF Pro Text', 14, 'bold')).pack(anchor='center', pady=(0, 2))

        ### GOOGLE MAPS SUBHEADING
        tk.Label(google_maps_search_card, text="Search keyword", bg=self.colors['card_bg'], fg=self.colors['text'],
        font=('SF Pro Text', 10, 'bold')).pack(anchor='w', pady=(0, 2))

        gm_loc_row = tk.Frame(google_maps_search_card, bg='#2A3441')
        gm_loc_row.pack(fill='x', pady=(0, 2))
        gm_location_entry = tk.Entry(gm_loc_row, textvariable=self.google_maps_keyword_search_var,
                                bg='#2A3441', fg=self.colors['text'],
                                borderwidth=0, relief='flat',
                                font=('SF Pro Text', 11),
                                insertbackground=self.colors['accent'])
        gm_location_entry.pack(side='left', fill='x', expand=True, padx=10, pady=4)

        tk.Label(google_maps_search_card, text="e.g., Doctors, Clinics, or Pharmacies...",
                bg=self.colors['card_bg'], fg=self.colors['text_secondary'],
                font=('SF Pro Text', 9)).pack(anchor='w', pady=(0, 2))

        ### RADIO BUTTONS
        # Initialize the keyword search var with empty value initially
        if not hasattr(self, "google_maps_keyword_search_var"):
            self.google_maps_keyword_search_var = tk.StringVar(value="")

        # Create a separate variable for radio button selection
        if not hasattr(self, "google_maps_radio_var"):
            self.google_maps_radio_var = tk.StringVar(value="NONE_SELECTED")  # Use a value that doesn't match any radio

        ### IF SEARCH INPUT KEY IS EMPTY, SET YELLOWPAGES TO FALSE
        if "GoogleMaps" not in self.providers:
            self.providers["GoogleMaps"] = tk.BooleanVar(value=False)
            
        def _sync_gmaps_provider(*_):
            """Enable Google Maps source whenever there's a non-empty keyword."""
            kw = self.google_maps_keyword_search_var.get().strip()
            self.providers["GoogleMaps"].set(bool(kw))

        # Update on any change to the keyword var
        self.google_maps_keyword_search_var.trace_add("write", _sync_gmaps_provider)
        
        def on_gmaps_radio_select():
            """Update the keyword search field when radio button is selected"""
            selected = self.google_maps_radio_var.get()
            if selected and selected != "NONE_SELECTED":
                self.google_maps_keyword_search_var.set(selected)
            _sync_gmaps_provider()
            
        gm_rb_row = tk.Frame(google_maps_search_card, bg=self.colors['card_bg'])
        gm_rb_row.pack(fill='x', pady=(2, 2))

        # a centered strip that holds the radios
        gm_rb_strip = tk.Frame(gm_rb_row, bg=self.colors['card_bg'])
        gm_rb_strip.pack(anchor='w')

        _sync_gmaps_provider()
        
        for name, var in self.google_maps_facilities.items():
            tk.Radiobutton(
                gm_rb_strip,
                text=name,
                variable=self.google_maps_radio_var,  # Use the radio variable
                value=name,  # Use the name as the value
                command=on_gmaps_radio_select,  # Add callback function
                bg=self.colors['card_bg'],
                fg=self.colors['text'],
                activebackground=self.colors['card_bg'],
                activeforeground=self.colors['text'],
                selectcolor='#2A3441',   # inner circle color
                highlightthickness=0,
                font=('SF Pro Text', 10)
            ).pack(side='left', padx=10, pady=2)
            

        # === Categories (Medicare) — tighter gaps ===
        cat_card = tk.Frame(content_frame, bg=self.colors['card_bg'], pady=4, padx=12)
        cat_card.pack(fill='x', expand=False, pady=(0, 2)) 
        self._add_shadow_effect(cat_card)
        
        tk.Label(
            cat_card,
            text="Medicare",
            bg=self.colors['card_bg'],
            fg=self.colors['text'],
            font=('SF Pro Text', 14, 'bold')
        ).pack(anchor='center', pady=(0, 2))

        tk.Label(cat_card, text="Categories", bg=self.colors['card_bg'], fg=self.colors['text'],
                font=('SF Pro Text', 10, 'bold')).pack(anchor='w', pady=(0, 0))

        cats_grid = tk.Frame(cat_card, bg=self.colors['card_bg'])
        cats_grid.pack(fill='x')

        cols = 3
        r = c = 0
        for name, var in self.medicare_categories.items():
            cell = tk.Frame(cats_grid, bg=self.colors['card_bg'])
            cell.grid(row=r, column=c, sticky='w', padx=(0, 14), pady=2)
            self._create_modern_checkbox(cell, name, var)
            c += 1
            if c >= cols:
                c = 0
                r += 1

        # === Search button (still stateful) — smaller paddings ===
        button_frame = tk.Frame(content_frame, bg=self.colors['bg'])
        button_frame.pack(fill='x', pady=(2, 0))

        search_button_frame = tk.Frame(button_frame, bg=self.colors['bg'])
        search_button_frame.pack(anchor='center', pady=(0, 3))

        self.search_canvas = tk.Canvas(search_button_frame, width=220, height=48,
                                    bg=self.colors['bg'], highlightthickness=0, cursor='hand2')
        self.search_canvas.pack()

        def _draw_search_button(hover=False):
            c = self.search_canvas
            c.delete('all')
            if self.is_searching:
                color1, color2 = '#006B8A', '#004D66'
                label = "Scraping..."
            else:
                color1, color2 = ('#00E6FF', '#00B3DD') if hover else ('#00D4FF', '#0099CC')
                label = "Scrape"

            steps = 24
            for i in range(steps):
                t = i / steps
                r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
                r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
                r = int(r1 + (r2 - r1) * t); g = int(g1 + (g2 - g1) * t); b = int(b1 + (b2 - b1) * t)
                c.create_rectangle(2, 2 + (44/steps)*i, 218, 2 + (44/steps)*(i+1),
                                fill=f'#{r:02x}{g:02x}{b:02x}', outline="")
            c.create_text(110, 24, text=label, fill='white', font=('SF Pro Display', 13, 'bold'))

        def _on_hover_in(_):
            if not self.is_searching:
                _draw_search_button(True)

        def _on_hover_out(_):
            if not self.is_searching:
                _draw_search_button(False)

        def _on_click(_=None):
            if self.is_searching:
                return
            self.is_searching = True
            _draw_search_button()
            self.on_run()

        _draw_search_button()
        self.search_canvas.bind('<Enter>', _on_hover_in)
        self.search_canvas.bind('<Leave>', _on_hover_out)
        self.search_canvas.bind('<Button-1>', _on_click)
        self.bind('<Return>', _on_click)

        # Progress + inline status (created but not packed - will be packed by show_progress())
        self.progress_frame = tk.Frame(content_frame, bg=self.colors['bg'])
        self.status_label = tk.Label(self.progress_frame, textvariable=self.status_var,
                                    bg=self.colors['bg'], fg=self.colors['text_secondary'],
                                    font=('SF Pro Text', 10), anchor='w', justify='left')
        self.progress_canvas = tk.Canvas(self.progress_frame, height=4, bg=self.colors['bg'], highlightthickness=0)

        self._draw_search_button = _draw_search_button

        # Store references for potential cleanup
        self.main_canvas = canvas
        self.scrollable_frame = scrollable_frame
    
    def _create_card(self, parent, title, delay):
        """Create an animated card with title"""
        # This is just for the visual effect, actual card is created separately
        pass
    
    def _add_shadow_effect(self, widget):
        """Add shadow effect to widgets (simulated with borders)"""
        widget.configure(relief='flat', borderwidth=1)
    
    def _add_entry_animation(self, entry):
        """Add focus animations to entry widgets"""
        def on_focus_in(event):
            entry.configure(bg='#364152')
        
        def on_focus_out(event):
            entry.configure(bg='#2A3441')
        
        entry.bind('<FocusIn>', on_focus_in)
        entry.bind('<FocusOut>', on_focus_out)
    
    def _create_small_button(self, parent, text, command, side='left'):
        """Create smaller utility buttons"""
        button = tk.Button(parent, text=text, command=command,
                          bg='#374151', fg=self.colors['text_secondary'],
                          borderwidth=0, relief='flat',
                          font=('SF Pro Text', 9),
                          cursor='hand2', padx=12, pady=6)
        button.pack(side=side, padx=8)
        
        def on_hover_enter(event):
            button.configure(bg='#4B5563', fg=self.colors['text'])
        
        def on_hover_leave(event):
            button.configure(bg='#374151', fg=self.colors['text_secondary'])
        
        button.bind('<Enter>', on_hover_enter)
        button.bind('<Leave>', on_hover_leave)
    
    def _create_modern_checkbox(self, parent, text, variable):
        """Create a modern custom checkbox"""
        frame = tk.Frame(parent, bg=self.colors['card_bg'])
        frame.pack(fill='x')
        
        # Custom checkbox canvas - made smaller
        cb_canvas = tk.Canvas(frame, width=16, height=16, bg=self.colors['card_bg'],
                            highlightthickness=0, cursor='hand2')
        cb_canvas.pack(side='left', padx=(0, 8))
        
        # Label
        label = tk.Label(frame, text=text, bg=self.colors['card_bg'], 
                        fg=self.colors['text'], font=('SF Pro Text', 10),
                        cursor='hand2')
        label.pack(side='left')
        
        def toggle_checkbox(event=None):
            variable.set(not variable.get())
            update_checkbox()
        
        def update_checkbox():
            cb_canvas.delete('all')
            if variable.get():
                # Checked state - filled circle with checkmark (adjusted for smaller size)
                cb_canvas.create_oval(1, 1, 15, 15, fill=self.colors['accent'], 
                                    outline=self.colors['accent'], width=1)
                cb_canvas.create_line(4, 8, 7, 11, fill='white', width=2)
                cb_canvas.create_line(7, 11, 12, 5, fill='white', width=2)
            else:
                # Unchecked state - circle outline (adjusted for smaller size)
                cb_canvas.create_oval(1, 1, 15, 15, fill='', 
                                    outline=self.colors['text_secondary'], width=1)
        
        # Bind clicks
        cb_canvas.bind('<Button-1>', toggle_checkbox)
        label.bind('<Button-1>', toggle_checkbox)
        
        # Initial state
        update_checkbox()
        
        return frame
    
    def _create_gradient_button(self, parent, text, command, primary=True, large=False):
        """Create a gradient button with hover effects"""
        button_frame = tk.Frame(parent, bg=self.colors['bg'])
        
        if primary:
            button_frame.pack(side='top', pady=10)  # Center the main button
        else:
            button_frame.pack(side='bottom', pady=(5, 0))
        
        # Button dimensions
        width = 200 if large else 120
        height = 50 if large else 35
        
        # Create canvas for gradient
        canvas = tk.Canvas(button_frame, width=width, height=height, 
                          bg=self.colors['bg'], highlightthickness=0,
                          cursor='hand2')
        canvas.pack()
        
        # Colors for gradient
        if primary:
            color1, color2 = '#00D4FF', '#0099CC'  # Bright blue gradient
            text_color = 'white'
            font_size = 13 if large else 11
            font_weight = 'bold'
        else:
            color1, color2 = '#4A5568', '#2D3748'
            text_color = self.colors['text_secondary']
            font_size = 10
            font_weight = 'normal'
        
        def draw_gradient(c1, c2, hover=False):
            canvas.delete('all')
            
            # Draw rounded rectangle background
            if hover and primary:
                # Brighter colors on hover
                c1, c2 = '#00E6FF', '#00B3DD'
            
            # Simple gradient simulation with rounded corners
            steps = 25
            corner_radius = 8
            
            for i in range(steps):
                ratio = i / steps
                r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
                r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
                
                r = int(r1 + (r2 - r1) * ratio)
                g = int(g1 + (g2 - g1) * ratio)
                b = int(b1 + (b2 - b1) * ratio)
                
                color = f'#{r:02x}{g:02x}{b:02x}'
                
                # Create gradient strips
                strip_height = height / steps
                canvas.create_rectangle(corner_radius, i * strip_height, 
                                      width - corner_radius, (i + 1) * strip_height, 
                                      fill=color, outline=color)
            
            # Add rounded corners (simple approximation)
            canvas.create_oval(0, 0, corner_radius*2, corner_radius*2, 
                             fill=c1, outline=c1)
            canvas.create_oval(width-corner_radius*2, 0, width, corner_radius*2, 
                             fill=c1, outline=c1)
            canvas.create_oval(0, height-corner_radius*2, corner_radius*2, height, 
                             fill=c2, outline=c2)
            canvas.create_oval(width-corner_radius*2, height-corner_radius*2, width, height, 
                             fill=c2, outline=c2)
            
            # Button text
            canvas.create_text(width/2, height/2, text=text, fill=text_color, 
                             font=('SF Pro Text', font_size, font_weight))
            
            # Add subtle border for definition
            if primary:
                canvas.create_rectangle(1, 1, width-1, height-1, outline='#00A3CC', width=1)
        
        def on_hover_enter(event):
            draw_gradient(color1, color2, hover=True)
            if primary:
                canvas.configure(cursor='hand2')
        
        def on_hover_leave(event):
            draw_gradient(color1, color2, hover=False)
        
        def on_click(event):
            # Visual click feedback
            draw_gradient('#006B8A', '#004D66', hover=False) if primary else None
            canvas.after(100, lambda: draw_gradient(color1, color2, hover=False))
            command()
        
        # Initial draw
        draw_gradient(color1, color2)
        
        # Bind events
        canvas.bind('<Enter>', on_hover_enter)
        canvas.bind('<Leave>', on_hover_leave)
        canvas.bind('<Button-1>', on_click)

    
    def _add_animations(self):
        """Add subtle animations to the interface"""
        # Fade in animation could be added here
        pass
    
    def _center_window(self):
        """Center the window on screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def show_progress(self):
        """Show animated progress indicator + inline status text"""
        self.progress_frame.pack(fill='x', pady=(10, 0))
    
        # Set wraplength to match the frame width for text wrapping
        self.progress_frame.update_idletasks()
        frame_width = self.progress_frame.winfo_width()
        if frame_width > 1:  # Ensure we have a valid width
            self.status_label.config(wraplength=frame_width - 20)  # Subtract padding
        
        # Pack status label first, then the bar
        self.status_label.pack(fill='x', padx=2, pady=(0, 6))
        self.progress_canvas.pack(fill='x')

        def animate_progress():
            self.progress_canvas.delete('all')
            width = self.progress_canvas.winfo_width() or 1
            
            # Create moving gradient bar
            for i in range(width):
                alpha = (math.sin(i * 0.1 + self.animation_step * 0.5) + 1) / 2
                intensity = int(255 * alpha * 0.6)
                color = f'#{intensity:02x}{intensity:02x}FF'
                self.progress_canvas.create_line(i, 0, i, 6, fill=color)
            
            # Update animation step for the next frame
            self.animation_step += 1

            # Call animate_progress again after 50ms for the next frame
            self.progress_canvas.after(50, animate_progress)

        # Initialize animation step and start animation
        self.animation_step = 0
        animate_progress()

    def hide_progress(self):
        """Hide progress indicator"""
        self.progress_frame.pack_forget()
    
    def on_run(self):
        """Handle run button click with validation and inline feedback"""
        location = self.location_var.get().strip()
        yellow_pages_keyword_search = self.yellow_pages_keyword_search_var.get().strip()
        google_maps_keyword_search = self.google_maps_keyword_search_var.get().strip()
        try:
            limit = int(self.limit_var.get())
        except ValueError:
            limit = 0
        try:
            radius = int(self.radius_var.get())
        except ValueError:
            radius = 0

        sources = {
            "YellowPages": self.providers["YellowPages"].get(),
            "GoogleMaps": self.providers["GoogleMaps"].get(),
        }
        
        medicare_categories = {
            "Physician": self.medicare_categories["Physician"].get(),
            "Hospital": self.medicare_categories["Hospital"].get(),
            "NursingHome": self.medicare_categories["Nursing Home"].get(),
            "HomeHealth": self.medicare_categories["Home Health"].get(),
            "Hospice": self.medicare_categories["Hospice"].get(),
            "DialysisFacility": self.medicare_categories["Dialysis Facility"].get(),
            "InpatientRehabilitation": self.medicare_categories["Inpatient Rehabilitation"].get(),
            "LongTermCare" : self.medicare_categories["Long Term Care"].get(), 
        }

        # Validation (keep your existing error popups if you like)
        if not location:
            self._show_modern_error("Please enter a search location")
            self.is_searching = False
            return
       
        if limit < 1:
            self._show_modern_error("Result limit must be at least 1")
            self.is_searching = False
            return
        
        if radius not in range(5, 255, 5):
            self._show_modern_error("Please select a valid search radius")
            self.is_searching = False
            return
        
        if not any(medicare_categories.values()) and not yellow_pages_keyword_search and not google_maps_keyword_search:
            self._show_modern_error("Please enter at least one keyword to search for Yellow Pages, Google Maps, or Medicare")
            self.is_searching = False
            return

        # Inline status + progress (no success popup)
        self.status_var.set(
            f"Searching at location {location} • Limit {limit} • Radius {radius} mi • "
            f"Sources: {', '.join([k for k,v in sources.items() if v] + (['Medicare'] if any(medicare_categories.values()) else []))}"
        )
        self.show_progress()

        # print parameters for debugging
        print("Running with parameters:")
        print(f"Location: {location}")
        print(f"Yellow Pages Keyword Search: {yellow_pages_keyword_search}")
        print(f"Google Maps Keyword Search: {google_maps_keyword_search}")
        print(f"Limit: {limit}")
        print(f"Radius: {radius} miles")
        print(f"Sources: {', '.join([k for k,v in sources.items() if v])}")
        print(f"Medicare Categories: {', '.join([k for k,v in medicare_categories.items() if v])}")
        
        # Kick off scraping in a background thread
        active_medicare_categories = {k: v for k, v in medicare_categories.items() if v is True}
        t = threading.Thread(
            target=self._run_pipeline_bg,
            args=(location, yellow_pages_keyword_search, google_maps_keyword_search, limit, radius, sources, active_medicare_categories),
            daemon=True
        )
        t.start()

    def _run_pipeline_bg(self, location, yellow_pages_keyword_search, google_maps_keyword_search, limit, radius, sources, medicare_categories):
        """Background thread: run pipeline and update UI when done."""
        try:
            summary = main_v1.run(
                location=location,
                yp_keyword=yellow_pages_keyword_search,
                gmaps_keyword=google_maps_keyword_search,
                limit=limit,
                radius_miles=radius,
                sources=sources,
                medicare_categories=medicare_categories
            )
            # Update the UI on the main thread
            def _done(summary):
                # Always stop the spinner / reset state
                self.is_searching = False
                self.hide_progress()

                # Guard: summary might be None or not a dict
                if not isinstance(summary, dict):
                    self._show_modern_error(
                        "No summary was returned by the scraping pipeline.\n\n"
                        "Please check the console/logs for errors."
                    )
                    # restore the Search button label if you use the custom canvas drawer
                    if hasattr(self, "_draw_search_button"):
                        self._draw_search_button()
                    return

                counts = summary.get("counts") or {}
                outfile = summary.get("outfile") or "output.xlsx"
                errors = summary.get("errors") or []

                # Build success message
                total = sum(counts.values()) if counts else 0
                success_message = (
                    f"Results saved to: {outfile}\n\n"
                    f"Medicare: {counts.get('Medicare', 0)} results\n"
                    f"YellowPages: {counts.get('YellowPages', 0)} results\n"
                    f"GoogleMaps: {counts.get('GoogleMaps', 0)} results\n\n"
                    f"Total: {total} results found"
                )

                if errors:
                    success_message += "\n\nErrors:\n- " + "\n- ".join(errors)

                self._show_modern_success(success_message)

                if hasattr(self, "_draw_search_button"):
                    self._draw_search_button()

            self.after(0, _done(summary))
            print(f"Summary {summary}")
            # app.destroy()
            # main_v1.hello()

        except Exception as e:
            print(e)
            def _err():
                self.hide_progress()
                self._show_modern_error(f"Search failed")
            self.after(0, _err)

    
    def _show_modern_error(self, message):
        """Show modern styled error message"""
        # Create custom error dialog
        error_window = tk.Toplevel(self)
        error_window.title("Validation Error")
        error_window.geometry("350x150")
        error_window.resizable(False, False)
        error_window.configure(bg=self.colors['bg'])
        error_window.transient(self)
        error_window.grab_set()
        
        # Center the error window
        error_window.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (350 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (150 // 2)
        error_window.geometry(f'350x200+{x}+{y}')
        
        # Error content
        tk.Label(error_window, text="⚠️", bg=self.colors['bg'], fg=self.colors['error'],
                font=('SF Pro Display', 24)).pack(pady=15)
        
        tk.Label(error_window, text=message, bg=self.colors['bg'], fg=self.colors['text'],
                font=('SF Pro Text', 11), wraplength=300).pack(pady=(0, 15))
        
        tk.Button(error_window, text="OK", command=error_window.destroy,
                 bg=self.colors['error'], fg='white', borderwidth=0,
                 font=('SF Pro Text', 10, 'bold'), cursor='hand2').pack()
    
    # Keeping this in case you want to bring back a success popup later.    
    def _show_modern_success(self, message):
        """Show modern styled success message"""
        # Create custom success dialog
        success_window = tk.Toplevel(self)
        success_window.title("Scrape Complete")
        success_window.geometry("400x400")
        success_window.resizable(False, False)
        success_window.configure(bg=self.colors['bg'])
        success_window.transient(self)
        success_window.grab_set()
        
        # Center the success window
        success_window.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (400 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (200 // 2)
        success_window.geometry(f'400x400+{x}+{y}')
        
        # Success content
        tk.Label(success_window, text="✅", bg=self.colors['bg'], fg=self.colors.get('success', '#28a745'),
                font=('SF Pro Display', 32)).pack(pady=20)
        
        tk.Label(success_window, text="Scraping Complete!", bg=self.colors['bg'], fg=self.colors['text'],
                font=('SF Pro Text', 14, 'bold')).pack(pady=(0, 10))
        
        tk.Label(success_window, text=message, bg=self.colors['bg'], fg=self.colors['text'],
                font=('SF Pro Text', 11), wraplength=350, justify='center').pack(pady=(0, 20))
        
        tk.Button(success_window, text="OK", command=success_window.destroy,
                bg=self.colors.get('success', '#28a745'), fg='white', borderwidth=0,
                font=('SF Pro Text', 10, 'bold'), cursor='hand2', padx=20).pack()

if __name__ == "__main__":
    # Try to use better fonts if available
    try:
        import matplotlib.font_manager as fm
        # You could add custom font loading here
    except ImportError:
        pass
    
    app = ModernGUI()
    app.mainloop()
