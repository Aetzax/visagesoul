/*
 * pam_visagesoul.c
 * Linux Pluggable Authentication Module (PAM) for VisageSoul Biometric Face Recognition.
 *
 * Designed for SDDM, KDE Lock Screen, GDM, sudo, and polkit.
 */

#define PAM_SM_AUTH
#define PAM_SM_ACCOUNT
#define PAM_SM_SESSION
#define PAM_SM_PASSWORD

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <syslog.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <signal.h>
#include <security/pam_appl.h>
#include <security/pam_modules.h>
#include <security/pam_ext.h>

#define MODULE_NAME "pam_visagesoul"
#define DEFAULT_VERIFY_PATH "/usr/local/bin/visagesoul-verify"
#define OPT_VERIFY_PATH "/opt/visagesoul/bin/visagesoul-verify"
#define FALLBACK_VERIFY_PATH "/usr/bin/visagesoul-verify"
#define LEGACY_VERIFY_PATH "/usr/local/bin/aura-verify"

#define FACES_DIR "/etc/visagesoul/faces"
#define LEGACY_FACES_DIR "/etc/aura-auth/faces"

static void send_pam_info(pam_handle_t *pamh, const char *message) {
    struct pam_conv *conv;
    int retval = pam_get_item(pamh, PAM_CONV, (const void **)&conv);
    if (retval != PAM_SUCCESS || conv == NULL || conv->conv == NULL) {
        return;
    }

    struct pam_message msg;
    const struct pam_message *msgp = &msg;
    struct pam_response *resp = NULL;

    msg.msg_style = PAM_TEXT_INFO;
    msg.msg = message;

    conv->conv(1, &msgp, &resp, conv->appdata_ptr);
    if (resp != NULL) {
        if (resp->resp != NULL) free(resp->resp);
        free(resp);
    }
}

static int is_valid_username(const char *username) {
    if (!username || strlen(username) == 0 || strlen(username) > 64) return 0;
    for (size_t i = 0; username[i] != '\0'; i++) {
        char c = username[i];
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.')) {
            return 0;
        }
    }
    if (strstr(username, "..")) return 0;
    return 1;
}

static int profile_exists(const char *username) {
    if (!is_valid_username(username)) return 0;
    char path[512];
    struct stat st;

    snprintf(path, sizeof(path), "%s/%s.json", FACES_DIR, username);
    if (stat(path, &st) == 0 && S_ISREG(st.st_mode)) return 1;

    snprintf(path, sizeof(path), "%s/%s.json", LEGACY_FACES_DIR, username);
    if (stat(path, &st) == 0 && S_ISREG(st.st_mode)) return 1;

    return 0;
}

static const char *get_verify_binary_path() {
    struct stat st;
    if (stat(DEFAULT_VERIFY_PATH, &st) == 0 && (st.st_mode & S_IXUSR)) return DEFAULT_VERIFY_PATH;
    if (stat(OPT_VERIFY_PATH, &st) == 0 && (st.st_mode & S_IXUSR)) return OPT_VERIFY_PATH;
    if (stat(FALLBACK_VERIFY_PATH, &st) == 0 && (st.st_mode & S_IXUSR)) return FALLBACK_VERIFY_PATH;
    if (stat(LEGACY_VERIFY_PATH, &st) == 0 && (st.st_mode & S_IXUSR)) return LEGACY_VERIFY_PATH;
    return NULL;
}

#include <pwd.h>

static void get_config_pam_settings(const char *username, int *out_notify, char *out_message, size_t max_len) {
    *out_notify = 1;
    strncpy(out_message, "Iniciando sesión con VisageSoul...", max_len - 1);
    out_message[max_len - 1] = '\0';

    char user_config_path[512] = "";
    if (username && strlen(username) > 0) {
        struct passwd *pw = getpwnam(username);
        if (pw && pw->pw_dir) {
            snprintf(user_config_path, sizeof(user_config_path), "%s/.config/visagesoul/config.ini", pw->pw_dir);
        }
    }

    const char *config_paths[3];
    int num_paths = 0;
    if (strlen(user_config_path) > 0) {
        config_paths[num_paths++] = user_config_path;
    }
    config_paths[num_paths++] = "/etc/visagesoul/config.ini";
    config_paths[num_paths++] = "/etc/aura-auth/config.ini";

    for (int p = 0; p < num_paths; p++) {
        FILE *fp = fopen(config_paths[p], "r");
        if (!fp) continue;

        char line[256];
        int in_pam_section = 0;
        while (fgets(line, sizeof(line), fp)) {
            char *trimmed = line;
            while (*trimmed == ' ' || *trimmed == '\t') trimmed++;
            if (*trimmed == '#' || *trimmed == ';') continue;

            if (*trimmed == '[' && strstr(trimmed, "pam")) {
                in_pam_section = 1;
                continue;
            } else if (*trimmed == '[') {
                in_pam_section = 0;
            }

            if (in_pam_section) {
                if (strncmp(trimmed, "notify", 6) == 0) {
                    char *val = strchr(trimmed, '=');
                    if (val) {
                        val++;
                        while (*val == ' ' || *val == '\t') val++;
                        if (strncmp(val, "true", 4) == 0 || strncmp(val, "1", 1) == 0) {
                            *out_notify = 1;
                        } else if (strncmp(val, "false", 5) == 0 || strncmp(val, "0", 1) == 0) {
                            *out_notify = 0;
                        }
                    }
                } else if (strncmp(trimmed, "message", 7) == 0) {
                    char *val = strchr(trimmed, '=');
                    if (val) {
                        val++;
                        while (*val == ' ' || *val == '\t') val++;
                        char *nl = strpbrk(val, "\r\n");
                        if (nl) *nl = '\0';
                        if (strlen(val) > 0) {
                            strncpy(out_message, val, max_len - 1);
                            out_message[max_len - 1] = '\0';
                        }
                    }
                }
            }
        }
        fclose(fp);
        break;
    }
}

PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    (void)flags;
    const char *username = NULL;
    int debug = 0;

    int retval = pam_get_user(pamh, &username, NULL);
    if (retval != PAM_SUCCESS || username == NULL || strlen(username) == 0) {
        return PAM_USER_UNKNOWN;
    }

    int cfg_notify = 1;
    char pam_message[256];
    get_config_pam_settings(username, &cfg_notify, pam_message, sizeof(pam_message));
    int notify = cfg_notify;

    for (int i = 0; i < argc; i++) {
        if (strcmp(argv[i], "debug") == 0) debug = 1;
        if (strcmp(argv[i], "notify") == 0) notify = 1;
        if (strcmp(argv[i], "no_notify") == 0) notify = 0;
    }

    if (debug) {
        openlog(MODULE_NAME, LOG_PID | LOG_CONS, LOG_AUTHPRIV);
        syslog(LOG_DEBUG, "Authenticating request started for user '%s'", username);
    }

    /* Fast exit if user is not enrolled in VisageSoul */
    if (!profile_exists(username)) {
        if (debug) syslog(LOG_DEBUG, "User '%s' is not enrolled in VisageSoul. Skipping.", username);
        return PAM_IGNORE;
    }

    const char *verify_bin = get_verify_binary_path();
    if (!verify_bin) {
        if (debug) syslog(LOG_ERR, "VisageSoul verify executable not found in system paths.");
        return PAM_AUTHINFO_UNAVAIL;
    }

    if (notify) {
        send_pam_info(pamh, pam_message);
    }

    /* Spawn verification process in isolated child */
    pid_t pid = fork();
    if (pid < 0) {
        if (debug) syslog(LOG_ERR, "Failed to fork verification process");
        return PAM_AUTH_ERR;
    }

    if (pid == 0) {
        /* Child process: silence C++ logging to terminal unless debug is explicitly requested */
        if (!debug) {
            int devnull = open("/dev/null", O_RDWR);
            if (devnull >= 0) {
                dup2(devnull, STDOUT_FILENO);
                dup2(devnull, STDERR_FILENO);
                close(devnull);
            }
        }

        char *args[] = {
            (char *)verify_bin,
            "--user",
            (char *)username,
            NULL
        };
        execv(verify_bin, args);
        exit(127);
    }

    /* Parent process: wait for child */
    int status = 0;
    pid_t wpid = waitpid(pid, &status, 0);

    if (wpid < 0) {
        if (debug) syslog(LOG_ERR, "waitpid failed on verification child process");
        return PAM_AUTH_ERR;
    }

    if (WIFEXITED(status)) {
        int exit_code = WEXITSTATUS(status);
        if (debug) syslog(LOG_DEBUG, "Verification process returned code: %d", exit_code);

        if (exit_code == 0) {
            if (debug) syslog(LOG_INFO, "User '%s' authenticated successfully via biometric face match.", username);
            return PAM_SUCCESS;
        } else if (exit_code == 3) {
            /* Max failed attempts exceeded -> force password entry */
            send_pam_info(pamh, "Límite de intentos faciales superado. Introduce tu contraseña.");
            return PAM_AUTH_ERR;
        } else if (exit_code == 2) {
            if (debug) syslog(LOG_NOTICE, "Camera unavailable or busy. Falling back.");
            return PAM_IGNORE;
        } else {
            if (debug) syslog(LOG_NOTICE, "Biometric match failed or timed out for '%s'.", username);
            return PAM_AUTH_ERR;
        }
    }

    return PAM_AUTH_ERR;
}

PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    (void)pamh; (void)flags; (void)argc; (void)argv;
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_acct_mgmt(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    (void)pamh; (void)flags; (void)argc; (void)argv;
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_open_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    (void)pamh; (void)flags; (void)argc; (void)argv;
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_close_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    (void)pamh; (void)flags; (void)argc; (void)argv;
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_chauthtok(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    (void)pamh; (void)flags; (void)argc; (void)argv;
    return PAM_SUCCESS;
}
