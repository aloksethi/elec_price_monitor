import zlib
import matplotlib.pyplot as plt
import numpy as np

WIDTH = 648
HEIGHT = 480

print("opening file")

with open("blk_buf_bin", "rb") as f:
    raw_bytes = zlib.decompress(f.read())

# Convert bytes to individual bits
bits = np.unpackbits(np.frombuffer(raw_bytes, dtype=np.uint8))

# Chop off any trailing byte padding to fit your exact resolution array
bits = bits[:(WIDTH * HEIGHT)]
pixel_grid = bits.reshape((HEIGHT, WIDTH))

# Map 0 to White and 1 to solid Red
cmap = plt.cm.colors.ListedColormap(['white', 'red'])

plt.figure(figsize=(10, 7))
plt.imshow(pixel_grid, cmap=cmap)
plt.title("Red Buffer Verification Grid")
plt.axis('off')
plt.show()
