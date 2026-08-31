CC ?= gcc
CFLAGS ?= -Wall -Wextra -O2 -fPIC
LDFLAGS ?= -shared -lpam

PREFIX ?= /usr/local
OPT_DIR ?= /opt/visagesoul
ETC_DIR ?= /etc/visagesoul
MODELS_DIR ?= /usr/share/visagesoul/models
PAM_LIB_DIR ?= /usr/lib/security

TARGET_PAM = pam_visagesoul.so
SRC_PAM = src/pam_visagesoul.c

.PHONY: all clean install uninstall download_models

all: $(TARGET_PAM) download_models

$(TARGET_PAM): $(SRC_PAM)
	$(CC) $(CFLAGS) $(LDFLAGS) $< -o $@

download_models:
	@./scripts/download_models.sh

install: all
	@echo "Installing VisageSoul system components..."

	# PAM Shared Library
	install -d $(DESTDIR)$(PAM_LIB_DIR)
	install -m 755 $(TARGET_PAM) $(DESTDIR)$(PAM_LIB_DIR)/$(TARGET_PAM)

	# Application in /opt/visagesoul
	install -d $(DESTDIR)$(OPT_DIR)
	install -d $(DESTDIR)$(OPT_DIR)/src
	install -d $(DESTDIR)$(OPT_DIR)/models
	install -d $(DESTDIR)$(OPT_DIR)/config
	install -d $(DESTDIR)$(MODELS_DIR)

	install -m 644 src/*.py $(DESTDIR)$(OPT_DIR)/src/
	install -m 644 models/* $(DESTDIR)$(OPT_DIR)/models/
	install -m 644 models/* $(DESTDIR)$(MODELS_DIR)/
	install -m 644 config/config.ini $(DESTDIR)$(OPT_DIR)/config/

	# Configuration and faces directory
	install -d -m 755 $(DESTDIR)$(ETC_DIR)
	install -d -m 1777 $(DESTDIR)$(ETC_DIR)/faces
	test -f $(DESTDIR)$(ETC_DIR)/config.ini || install -m 644 config/config.ini $(DESTDIR)$(ETC_DIR)/config.ini

	# Setup Python virtualenv inside /opt/visagesoul (if not already present)
	test -d $(DESTDIR)$(OPT_DIR)/venv || python3 -m venv $(DESTDIR)$(OPT_DIR)/venv
	$(DESTDIR)$(OPT_DIR)/venv/bin/pip install --upgrade pip opencv-python numpy PyQt6 mediapipe

	# Wrapper scripts in /usr/local/bin
	install -d $(DESTDIR)$(PREFIX)/bin
	@echo '#!/bin/bash' > $(DESTDIR)$(PREFIX)/bin/visagesoul
	@echo 'exec /opt/visagesoul/venv/bin/python /opt/visagesoul/src/cli.py "$$@"' >> $(DESTDIR)$(PREFIX)/bin/visagesoul
	@chmod 755 $(DESTDIR)$(PREFIX)/bin/visagesoul

	@echo '#!/bin/bash' > $(DESTDIR)$(PREFIX)/bin/visagesoul-verify
	@echo 'exec /opt/visagesoul/venv/bin/python /opt/visagesoul/src/verify.py "$$@"' >> $(DESTDIR)$(PREFIX)/bin/visagesoul-verify
	@chmod 755 $(DESTDIR)$(PREFIX)/bin/visagesoul-verify

	# Alias for aura
	@echo '#!/bin/bash' > $(DESTDIR)$(PREFIX)/bin/aura
	@echo 'exec /usr/local/bin/visagesoul "$$@"' >> $(DESTDIR)$(PREFIX)/bin/aura
	@chmod 755 $(DESTDIR)$(PREFIX)/bin/aura

	# Polkit Policy
	install -d $(DESTDIR)/usr/share/polkit-1/actions
	install -m 644 config/org.visagesoul.policy $(DESTDIR)/usr/share/polkit-1/actions/org.visagesoul.policy

	# Assets & Icons
	install -d $(DESTDIR)$(OPT_DIR)/assets
	install -m 644 assets/* $(DESTDIR)$(OPT_DIR)/assets/
	install -d $(DESTDIR)/usr/share/icons/hicolor/scalable/apps
	install -m 644 assets/visagesoul.svg $(DESTDIR)/usr/share/icons/hicolor/scalable/apps/visagesoul.svg
	install -d $(DESTDIR)/usr/share/pixmaps
	install -m 644 assets/visagesoul.svg $(DESTDIR)/usr/share/pixmaps/visagesoul.svg
	install -m 644 assets/visagesoul.png $(DESTDIR)/usr/share/pixmaps/visagesoul.png

	# Desktop Launcher
	install -d $(DESTDIR)/usr/share/applications
	install -m 644 visagesoul.desktop $(DESTDIR)/usr/share/applications/visagesoul.desktop

uninstall:
	@echo "Uninstalling VisageSoul..."
	/usr/local/bin/visagesoul uninstall || true

clean:
	rm -f $(TARGET_PAM) pam_aura_auth.so
