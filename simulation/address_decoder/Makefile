SIM ?= questa
GUI ?= 0
TOPLEVEL_LANG ?= vhdl
DESIGN ?= l1calogfex
VCOM_ARGS=-2008
export COCOTB_RESOLVE_X=RANDOM

PWD=$(shell pwd)

export PYTHONPATH := $(PWD)/../../edawishlist:$(PYTHONPATH)

VHDL_SOURCES = $(PWD)/../../firmware/$(DESIGN)_pkg.vhd
VHDL_SOURCES += $(PWD)/../../firmware/$(DESIGN)_address_decoder.vhd
VHDL_SOURCES += $(PWD)/../../firmware/$(DESIGN)_instantiation.vhd

export BACKANNOTATED_YAML := $(PWD)/../../firmware/$(DESIGN)_backannotated.yaml

TOPLEVEL := $(DESIGN)_address_decoder
MODULE   := rtl_simulation

include $(shell cocotb-config --makefiles)/Makefile.sim
