# Maintainer: aetzax <aetzax@local>
pkgname=visagesoul
pkgver=1.0.0
pkgrel=1
pkgdesc="Next-generation biometric facial & gestural authentication for Linux (SDDM, KDE Plasma, sudo)"
arch=('x86_64')
url="https://github.com/visagesoul/visagesoul"
license=('GPL3')
depends=('pam' 'python' 'opencv' 'python-numpy' 'python-pyqt6' 'polkit' 'v4l-utils' 'libcanberra')
makedepends=('gcc' 'make' 'curl')
source=()

build() {
    cd "$srcdir/.."
    make all
}

package() {
    cd "$srcdir/.."
    make DESTDIR="$pkgdir" install
}
