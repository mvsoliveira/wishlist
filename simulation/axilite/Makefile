SIM ?= questa
GUI ?= 0
WAVES ?= 1
TOPLEVEL_LANG ?= vhdl
DESIGN ?= example
VCOM_ARGS=-2008
export COCOTB_RESOLVE_X=RANDOM

PWD=$(shell pwd)

export PYTHONPATH := $(PWD)/../../wishlist:$(PYTHONPATH)
RTL_LIBRARY = axi_lite_ipif_v3_0_4
VHDL_SOURCES = axi_lite_ipif_v3_0_vh_rfs.vhd
VHDL_SOURCES += $(PWD)/../../firmware/$(DESIGN)_pkg.vhd
VHDL_SOURCES += $(PWD)/../../firmware/$(DESIGN)_address_decoder.vhd
VHDL_SOURCES += $(PWD)/../../firmware/$(DESIGN)_axilite.vhd

export BACKANNOTATED_YAML := $(PWD)/../../firmware/$(DESIGN)_backannotated.yaml

TOPLEVEL := $(DESIGN)_axilite
MODULE   := axilite_simulation

include $(shell cocotb-config --makefiles)/Makefile.sim
