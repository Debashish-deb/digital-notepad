# @File(label="Select a slide to process") filename
# @File(label="Select the output location", style="directory") output_dir
# @String(label="Experiment name (base name for output files)") experiment_name
# @Float(label="Flat field smoothing parameter (0 for automatic)", value=0.1) lambda_flat
# @Float(label="Dark field smoothing parameter (0 for automatic)", value=0.01) lambda_dark

# Takes a slide (or other multi-series BioFormats-compatible file set) and
# generates flat- and dark-field correction profile images with BaSiC. The
# output format is two multi-series TIFF files (one for flat and one for dark)
# which is the input format used by Ashlar.
#
# Invocation:
# ImageJ --ij2 --headless --run imagej_basic_ashlar.py \
#   "filename='input.ext',output_dir='output',experiment_name='my_experiment'"

from ij import IJ, WindowManager, Prefs
from ij.macro import Interpreter
from loci.plugins import BF
from loci.formats import ImageReader
import BaSiC_ as Basic

ImporterOptions = __import__(
    "loci.plugins.in", fromlist=["ImporterOptions"]
).ImporterOptions
DynamicMetadataOptions = __import__(
    "loci.formats.in", fromlist=["DynamicMetadataOptions"]
).DynamicMetadataOptions


def main():
    Interpreter.batchMode = True

    if (lambda_flat == 0) ^ (lambda_dark == 0):
        print("ERROR: Both of lambda_flat and lambda_dark must be zero, or both non-zero.")
        return

    lambda_estimate = "Automatic" if lambda_flat == 0 else "Manual"

    print("Loading images...")
    print("Input file   : {}".format(filename))
    print("Output dir   : {}".format(output_dir))
    print("Experiment   : {}".format(experiment_name))
    print("Lambda flat  : {}".format(lambda_flat))
    print("Lambda dark  : {}".format(lambda_dark))

    # Avoid Bio-Formats autostitch/attachment series for CZI inputs.
    # This preserves the local workstation scientific behavior: BaSiC is
    # estimated from the raw/unstitched tile series.
    Prefs.set("bioformats.zeissczi.allow.autostitch", "false")
    Prefs.set("bioformats.zeissczi.include.attachments", "false")

    dyn_options = DynamicMetadataOptions()
    dyn_options.setBoolean("zeissczi.autostitch", False)
    dyn_options.setBoolean("zeissczi.attachments", False)

    bfreader = ImageReader()
    bfreader.setMetadataOptions(dyn_options)
    bfreader.setId(str(filename))

    num_images = bfreader.getSeriesCount()
    bfreader.setSeries(0)
    num_channels = bfreader.getSizeC()
    width = bfreader.getSizeX()
    height = bfreader.getSizeY()
    bfreader.close()

    print("Series count : {}".format(num_images))
    print("Channels     : {}".format(num_channels))
    print("Width        : {}".format(width))
    print("Height       : {}".format(height))

    # BaSiC requires the private noOfSlices field when called through scripting.
    no_of_slices_field = Basic.getDeclaredField("noOfSlices")
    no_of_slices_field.setAccessible(True)

    basic = Basic()
    no_of_slices_field.setInt(basic, num_images)

    ff_image = IJ.createImage("Flat-field", "32-bit black", width, height, num_channels)
    df_image = IJ.createImage("Dark-field", "32-bit black", width, height, num_channels)

    for channel in range(num_channels):
        print("")
        print("Processing channel {}/{}...".format(channel + 1, num_channels))
        print("===========================")

        options = ImporterOptions()
        options.setId(str(filename))
        options.setOpenAllSeries(True)
        options.setConcatenate(True)
        options.setAutoscale(False)
        options.setColorMode(ImporterOptions.COLOR_MODE_GRAYSCALE)

        for i in range(num_images):
            options.setCBegin(i, channel)
            options.setCEnd(i, channel)
            options.setZBegin(i, 0)
            options.setZEnd(i, 0)
            options.setTBegin(i, 0)
            options.setTEnd(i, 0)

        imps = BF.openImagePlus(options)
        if len(imps) == 0:
            print("ERROR: Bio-Formats did not open any images for channel {}".format(channel))
            return

        input_image = imps[0]
        WindowManager.setTempCurrentImage(input_image)

        input_title = input_image.getTitle()
        print("Opened stack   : {}".format(input_title))

        basic.exec(
            input_image, None, None,
            "Estimate shading profiles",
            "Estimate both flat-field and dark-field",
            lambda_estimate, lambda_flat, lambda_dark,
            "Ignore", "Compute shading only"
        )

        ff_channel = WindowManager.getImage("Flat-field:{}".format(input_title))
        if ff_channel is None:
            print("ERROR: Could not find BaSiC flat-field image for title {}".format(input_title))
            input_image.close()
            return

        df_channel = WindowManager.getImage("Dark-field:{}".format(input_title))
        if df_channel is None:
            print("ERROR: Could not find BaSiC dark-field image for title {}".format(input_title))
            ff_channel.close()
            input_image.close()
            return

        ff_image.setSlice(channel + 1)
        ff_image.getProcessor().insert(ff_channel.getProcessor(), 0, 0)

        df_image.setSlice(channel + 1)
        df_image.getProcessor().insert(df_channel.getProcessor(), 0, 0)

        ff_channel.close()
        df_channel.close()
        input_image.close()

    ff_filename = "{}/{}-ffp.tif".format(output_dir, experiment_name)
    df_filename = "{}/{}-dfp.tif".format(output_dir, experiment_name)

    IJ.saveAsTiff(ff_image, ff_filename)
    IJ.saveAsTiff(df_image, df_filename)

    ff_image.close()
    df_image.close()

    print("Done!")
    print("Saved flat-field: {}".format(ff_filename))
    print("Saved dark-field: {}".format(df_filename))


main()
