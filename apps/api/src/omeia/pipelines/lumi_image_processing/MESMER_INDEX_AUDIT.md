# Mesmer channel and output index audit

## Conclusion

Ada's output mapping is correct and must remain:

- `compartment="both"` output channel 0: whole-cell labels
- `compartment="both"` output channel 1: nuclear labels

The original script's nuclear mask uses output channel 0 only when it calls
Mesmer with `compartment="nuclear"`. That call has one output channel, so the
requested nuclear mask is necessarily channel 0. This does not imply that
nuclear is channel 0 in `compartment="both"`.

Changing Ada's nuclear extraction from index 1 to index 0 would save the
whole-cell mask under the nuclear filename.

## Two independent index spaces

### Input fluorescence channels

Mesmer input has shape `[batch, Y, X, 2]`:

- input channel 0: nuclear marker
- input channel 1: membrane or cytoplasm marker

The original script defaults the OME nuclear input channel to 0. Ada now
preserves that choice whenever OME channel 0 has a validated nuclear-marker
name. If channel 0 is not nuclear, Ada uses the first validated nuclear marker.
`PIPELINE_NUCLEAR_CHANNEL_OVERRIDE` remains available for an explicit choice.

### Output compartments

DeepCell's official `mesmer_postprocess` implementation behaves as follows:

- `compartment="nuclear"` calls nuclear watershed and returns one channel.
- `compartment="whole-cell"` calls whole-cell watershed and returns one
  channel.
- `compartment="both"` concatenates whole-cell first and nuclear second.

Ada always requests `both`, then separates and stitches the two label channels
independently. This matches both the reference script's `both` branch and the
official DeepCell implementation.

## Nuclear-only reference nuance

The reference script defaults to `compartment="nuclear"`. In that mode it
loads only the nuclear image, and its tile processor duplicates that image
into both Mesmer input slots. Therefore, a mask produced by the reference
script's default nuclear-only command can differ from the nuclear mask produced
by its own `compartment="both"` command, even though the nuclear watershed
logic is the same.

Ada must produce both masks, so the scientifically relevant comparison is the
reference script's `compartment="both"` branch:

- the same resolved nuclear OME channel is placed in Mesmer input channel 0;
- the membrane/cytoplasm OME channel is placed in Mesmer input channel 1;
- nuclear labels are extracted from `both` output channel 1.

Duplicating the nuclear image into the membrane slot in Ada would violate the
official two-channel input contract and remove the signal required for
whole-cell segmentation.

## Safeguards added

- Named constants distinguish input indices from output indices.
- The worker rejects `both` predictions that do not have exactly two channels.
- It rejects single-compartment predictions that do not have exactly one
  channel.
- Runtime logs print both the input and output mapping.
- Automatic nuclear input selection now prefers validated channel 0.
- A hard-coded access token found in an unused legacy script was removed.

## References

- Reference implementation: `/Users/debashishdeb/Documents/CSC/scripts/mesmer.py`
- Ada implementation:
  `/Users/debashishdeb/Documents/CSC/scripts/ada/scripts/2-segmentation/mesmer/mesmer.py`
- [Official DeepCell Mesmer source](https://github.com/vanvalenlab/deepcell-tf/blob/master/deepcell/applications/mesmer.py)
