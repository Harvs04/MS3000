# def _build_modern_ui(self):
    #     """Build the modern UI with cards and gradients"""
        
    #     # Header with gradient effect
    #     header_frame = tk.Frame(self, bg=self.colors['bg'], height=120)
    #     header_frame.pack(fill='x', padx=0, pady=0)
    #     header_frame.pack_propagate(False)
        
    #     # Animated gradient canvas
    #     self.gradient_canvas = tk.Canvas(header_frame, height=120, bg=self.colors['bg'], highlightthickness=0)
    #     self.gradient_canvas.pack(fill='both', expand=True)
        
    #     # Title and subtitle on gradient
    #     title = tk.Label(header_frame, text="🏥 Mark Scraper 3000", 
    #                     bg=self.colors['bg'], fg=self.colors['text'],
    #                     font=('SF Pro Display', 22, 'bold'))
    #     title.place(relx=0.5, rely=0.35, anchor='center')
        
    #     subtitle = tk.Label(header_frame, text="Find healthcare providers in your area", 
    #                        bg=self.colors['bg'], fg=self.colors['text_secondary'],
    #                        font=('SF Pro Display', 11))
    #     subtitle.place(relx=0.5, rely=0.65, anchor='center')
        
    #     # Main content area with cards
    #     content_frame = tk.Frame(self, bg=self.colors['bg'])
    #     content_frame.pack(fill='both', expand=True, padx=30, pady=0)
        
    #     # Location Card
    #     self._create_card(content_frame, "📍 Search Location", 0)
    #     location_card = tk.Frame(content_frame, bg=self.colors['card_bg'], pady=20, padx=25)
    #     location_card.pack(fill='x', pady=(0, 0))
    #     self._add_shadow_effect(location_card)
        
    #     tk.Label(location_card, text="Enter your location", 
    #             bg=self.colors['card_bg'], fg=self.colors['text'],
    #             font=('SF Pro Text', 11, 'bold')).pack(anchor='w', pady=(0, 8))
        
    #     # === Location entry row (Entry + inline Search button) ===
    #     entry_frame = tk.Frame(location_card, bg='#2A3441')
    #     entry_frame.pack(fill='x', pady=(0, 5))
        
    #     # Location entry (left, expands)
    #     location_entry = tk.Entry(
    #         entry_frame,
    #         textvariable=self.location_var,
    #         bg='#2A3441',
    #         fg=self.colors['text'],
    #         borderwidth=0,
    #         relief='flat',
    #         font=('SF Pro Text', 12),
    #         insertbackground=self.colors['accent']
    #     )
    #     location_entry.pack(side='left', fill='x', expand=True, padx=(15, 8), pady=2)

    #     tk.Label(location_card, text="e.g., Los Angeles, CA 90210", 
    #             bg=self.colors['card_bg'], fg=self.colors['text_secondary'],
    #             font=('SF Pro Text', 9)).pack(anchor='w')

    #     ### SEARCH QUERY
    #     tk.Label(location_card, text="Enter keyword", 
    #             bg=self.colors['card_bg'], fg=self.colors['text'],
    #             font=('SF Pro Text', 11, 'bold')).pack(anchor='w', pady=(0, 8))
        
    #     # === Location entry row (Entry + inline Search button) ===
    #     entry_frame = tk.Frame(location_card, bg='#2A3441')
    #     entry_frame.pack(fill='x', pady=(0, 5))
        
    #     # Location entry (left, expands)
    #     search_entry = tk.Entry(
    #         entry_frame,
    #         textvariable=self.keyword_search_var,
    #         bg='#2A3441',
    #         fg=self.colors['text'],
    #         borderwidth=0,
    #         relief='flat',
    #         font=('SF Pro Text', 12),
    #         insertbackground=self.colors['accent']
    #     )
    #     search_entry.pack(side='left', fill='x', expand=True, padx=(15, 8), pady=2)

    #     tk.Label(location_card, text="e.g., Doctor, Hospital, or Clinics", 
    #             bg=self.colors['card_bg'], fg=self.colors['text_secondary'],
    #             font=('SF Pro Text', 9)).pack(anchor='w')

    #     self._add_entry_animation(location_entry)
    #     self._add_entry_animation(search_entry)
        
    #     # Inline Search button (right)
    #     # inline_search_btn = tk.Button(
    #     #     entry_frame,
    #     #     text="Search",
    #     #     command=self.on_run,
    #     #     bg=self.colors['accent'],
    #     #     fg='white',
    #     #     activebackground=self.colors['accent_hover'],
    #     #     activeforeground='white',
    #     #     borderwidth=0,
    #     #     relief='flat',
    #     #     font=('SF Pro Text', 10, 'bold'),
    #     #     cursor='hand2',
    #     #     padx=12,
    #     #     pady=8
    #     # )
    #     # inline_search_btn.pack(side='right', padx=(0, 15), pady=8)
        
    #     # def _sb_enter(e):
    #     #     inline_search_btn.configure(bg=self.colors['accent_hover'])
    #     # def _sb_leave(e):
    #     #     inline_search_btn.configure(bg=self.colors['accent'])
    #     # inline_search_btn.bind('<Enter>', _sb_enter)
    #     # inline_search_btn.bind('<Leave>', _sb_leave)
        
    #     # Search Parameters Card
    #     params_card = tk.Frame(content_frame, bg=self.colors['card_bg'], pady=20, padx=25)
    #     params_card.pack(fill='x', pady=(0, 20))
    #     self._add_shadow_effect(params_card)

    #     tk.Label(params_card, text="Search Parameters", 
    #             bg=self.colors['card_bg'], fg=self.colors['text'],
    #             font=('SF Pro Text', 13, 'bold')).pack(anchor='w', pady=(0, 15))

    #     # Parameters grid (2 columns)
    #     params_grid = tk.Frame(params_card, bg=self.colors['card_bg'])
    #     params_grid.pack(fill='x')
        
    #     # Make both columns expand evenly
    #     params_grid.columnconfigure(0, weight=1)
    #     params_grid.columnconfigure(1, weight=1)

    #     # --- Left column: Result Limit ---
    #     limit_col = tk.Frame(params_grid, bg=self.colors['card_bg'])
    #     limit_col.grid(row=0, column=0, sticky='nsew', padx=(0, 10))

    #     tk.Label(limit_col, text="Result Limit", 
    #             bg=self.colors['card_bg'], fg=self.colors['text'],
    #             font=('SF Pro Text', 10, 'bold')).pack(anchor='w')

    #     limit_spinbox = tk.Spinbox(limit_col, from_=1, to=100000, textvariable=self.limit_var,
    #                             bg='#2A3441', fg=self.colors['text'], 
    #                             borderwidth=0, relief='flat',
    #                             buttonbackground=self.colors['accent'],
    #                             font=('SF Pro Text', 11), width=15)
    #     limit_spinbox.pack(anchor='w', pady=(5, 0), fill='x')

    #     # --- Right column: Search Radius ---
    #     radius_col = tk.Frame(params_grid, bg=self.colors['card_bg'])
    #     radius_col.grid(row=0, column=1, sticky='nsew', padx=(10, 0))

    #     tk.Label(radius_col, text="Search Radius (miles)", 
    #             bg=self.colors['card_bg'], fg=self.colors['text'],
    #             font=('SF Pro Text', 10, 'bold')).pack(anchor='w')

    #     miles = [str(i) for i in range(5, 255, 5)]
    #     radius_combo = ttk.Combobox(radius_col, values=miles, textvariable=self.radius_var,
    #                             state="readonly", width=15, style='Modern.TCombobox')
    #     radius_combo.pack(anchor='w', pady=(5, 0), fill='x')
        
    #     # Data Sources Card
    #     sources_card = tk.Frame(content_frame, bg=self.colors['card_bg'], pady=20, padx=25)
    #     sources_card.pack(fill='x', pady=(0, 25))
    #     self._add_shadow_effect(sources_card)
        
    #     tk.Label(sources_card, text="Data Sources", 
    #             bg=self.colors['card_bg'], fg=self.colors['text'],
    #             font=('SF Pro Text', 13, 'bold')).pack(anchor='w', pady=(0, 15))
        
    #     # Sources grid with modern checkboxes
    #     sources_grid = tk.Frame(sources_card, bg=self.colors['card_bg'])
    #     sources_grid.pack(fill='x')
        
    #     # Create custom checkboxes
    #     self.checkbox_frames = {}
    #     row, col = 0, 0
    #     for name, var in self.providers.items():
    #         cb_frame = tk.Frame(sources_grid, bg=self.colors['card_bg'])
    #         cb_frame.grid(row=row, column=col, sticky='w', padx=(0, 20), pady=5)
            
    #         self.checkbox_frames[name] = self._create_modern_checkbox(cb_frame, name, var)
            
    #         col += 1
    #         # change column here
    #         if col > 2: 
    #             col = 0
    #             row += 1
        
    #     # Action Button (Search only)
    #     button_frame = tk.Frame(content_frame, bg=self.colors['bg'])
    #     button_frame.pack(fill='x', pady=(0, 0))

    #     # Create the main search button - large and centered
    #     search_button_frame = tk.Frame(button_frame, bg=self.colors['bg'])
    #     search_button_frame.pack(anchor='center', pady=(0, 15))

    #     # Large search button
    #     search_canvas = tk.Canvas(
    #         search_button_frame, width=250, height=60,
    #         bg=self.colors['bg'], highlightthickness=0, cursor='hand2'
    #     )
    #     search_canvas.pack()

    #     def draw_search_button(hover=False):
    #         search_canvas.delete('all')

    #         # Button colors
    #         if hover:
    #             color1, color2 = '#00E6FF', '#00B3DD'
    #         else:
    #             color1, color2 = '#00D4FF', '#0099CC'

    #         # Gradient background
    #         steps = 30
    #         for i in range(steps):
    #             ratio = i / steps
    #             r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
    #             r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
    #             r = int(r1 + (r2 - r1) * ratio)
    #             g = int(g1 + (g2 - g1) * ratio)
    #             b = int(b1 + (b2 - b1) * ratio)
    #             color = f'#{r:02x}{g:02x}{b:02x}'
    #             strip_height = 52 / steps
    #             search_canvas.create_rectangle(
    #                 2, 2 + i * strip_height, 248, 2 + (i + 1) * strip_height,
    #                 fill=color, outline=color
    #             )

    #         # Text
    #         search_canvas.create_text(
    #             125, 30, text="Search", fill='white',
    #             font=('SF Pro Display', 14, 'bold')
    #         )

    #     def on_search_hover_enter(event):
    #         draw_search_button(hover=True)

    #     def on_search_hover_leave(event):
    #         draw_search_button(hover=False)

    #     def on_search_click(event):
    #         # Click animation
    #         search_canvas.delete('all')
    #         search_canvas.create_text(125, 30, text="Searching...", fill='white',
    #                                 font=('SF Pro Display', 14, 'bold'))
    #         search_canvas.after(150, lambda: draw_search_button(hover=False))
    #         search_canvas.after(200, self.on_run)

    #     # Initial draw + bindings
    #     draw_search_button()
    #     search_canvas.bind('<Enter>', on_search_hover_enter)
    #     search_canvas.bind('<Leave>', on_search_hover_leave)
    #     search_canvas.bind('<Button-1>', on_search_click)

    #     # Progress + inline status (kept)
    #     self.progress_frame = tk.Frame(content_frame, bg=self.colors['bg'])
    #     self.status_label = tk.Label(
    #         self.progress_frame, textvariable=self.status_var,
    #         bg=self.colors['bg'], fg=self.colors['text_secondary'],
    #         font=('SF Pro Text', 10), anchor='w', justify='left'
    #     )
    #     self.progress_canvas = tk.Canvas(
    #         self.progress_frame, height=6, bg=self.colors['bg'], highlightthickness=0
    #     )

    #     # Bind Enter key to start search
    #     self.bind('<Return>', lambda e: self.on_run())