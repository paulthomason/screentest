import RPi.GPIO as GPIO
from luma.core.interface.serial import spi as luma_spi, noop as luma_noop
import time
from PIL import Image, ImageDraw
import logging
import sys

# ---- LOGGING SETUP ----
logging.basicConfig(
    level=logging.DEBUG,
    filename="screen.txt",
    filemode="w",
    format="%(asctime)s [%(levelname)s] %(message)s"
)
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

# ---- PIN DEFINITIONS ----
DC = 25    # Data/Command
RST = 27   # Reset
CS = 8     # Chip select
BL = 24    # Backlight

# ---- LCD PARAMETERS ----
WIDTH = 128
HEIGHT = 128

# ---- SPI ----
SPI_PORT = 0
SPI_DEVICE = 0

# ---- LCD COMMANDS ----
ST7735_SWRESET = 0x01
ST7735_SLPOUT  = 0x11
ST7735_DISPON  = 0x29
ST7735_CASET   = 0x2A
ST7735_RASET   = 0x2B
ST7735_RAMWR   = 0x2C
ST7735_MADCTL  = 0x36
ST7735_COLMOD  = 0x3A

def write_command(spi_interface, cmd):
    """Send a command byte using the luma SPI interface."""
    # Chip Select is managed by the SPI interface
    spi_interface.command(cmd)
    logging.debug(f"Sent command: 0x{cmd:02X}")

def write_data(spi_interface, data):
    """Send raw data bytes using the luma SPI interface."""
    spi_interface.data(data)
    logging.debug(
        f"Sent data: {data[:16]}... ({len(data)} bytes)" if len(data) > 16 else f"Sent data: {data}"
    )

def lcd_init(spi):
    logging.info("Initializing LCD")
    GPIO.output(RST, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(RST, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(RST, GPIO.HIGH)
    time.sleep(0.1)

    write_command(spi, ST7735_SWRESET)
    time.sleep(0.15)
    write_command(spi, ST7735_SLPOUT)
    time.sleep(0.15)
    write_command(spi, ST7735_COLMOD)
    write_data(spi, [0x05])  # 16-bit color
    write_command(spi, ST7735_DISPON)
    time.sleep(0.1)
    logging.info("LCD initialization complete")

def set_window(spi, x0, y0, x1, y1):
    write_command(spi, ST7735_CASET)
    write_data(spi, [0x00, x0, 0x00, x1])
    write_command(spi, ST7735_RASET)
    write_data(spi, [0x00, y0, 0x00, y1])
    write_command(spi, ST7735_RAMWR)

def display_image(spi, img):
    logging.info("Displaying image on LCD")
    pix = img.convert("RGB").load()
    buf = []
    for y in range(HEIGHT):
        for x in range(WIDTH):
            r, g, b = pix[x, y]
            # Convert to 16-bit RGB565
            rgb = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            buf.append((rgb >> 8) & 0xFF)
            buf.append(rgb & 0xFF)
    set_window(spi, 0, 0, WIDTH-1, HEIGHT-1)
    write_data(spi, buf)
    logging.info("Image sent to LCD")

def main():
    logging.info("Program started")
    # GPIO setup
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(DC, GPIO.OUT)
    GPIO.setup(RST, GPIO.OUT)
    # The luma SPI interface manages the Chip Select line, so manual setup via
    # RPi.GPIO is unnecessary and can cause errors.
    # GPIO.setup(CS, GPIO.OUT)
    GPIO.setup(BL, GPIO.OUT)
    GPIO.output(BL, GPIO.HIGH)  # Backlight ON

    # SPI setup using luma.core serial interface
    try:
        spi = luma_spi(port=SPI_PORT, device=SPI_DEVICE, bus_speed_hz=4000000, gpio=luma_noop())
        logging.info(f"SPI opened (port {SPI_PORT}, device {SPI_DEVICE})")
    except Exception as e:
        logging.exception(f"SPI open failed: {e}")
        GPIO.cleanup()
        return

    try:
        lcd_init(spi)
        img_red = Image.new("RGB", (WIDTH, HEIGHT), (255, 0, 0))
        img_blue = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 255))
        while True:
            logging.info("Switching to RED")
            display_image(spi, img_red)
            time.sleep(5)
            logging.info("Switching to BLUE")
            display_image(spi, img_blue)
            time.sleep(5)
    except KeyboardInterrupt:
        logging.info("Program interrupted by user (CTRL+C)")
    except Exception as e:
        logging.exception(f"Error during display loop: {e}")
    finally:
        GPIO.output(BL, GPIO.LOW)  # Backlight OFF
        GPIO.cleanup()
        spi.cleanup()
        logging.info("GPIO cleaned up, SPI closed, exiting.")

if __name__ == "__main__":
    main()
