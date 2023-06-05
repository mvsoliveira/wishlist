SIM ?= questa
GUI ?= 1
TOPLEVEL_LANG ?= vhdl
VCOM_ARGS=-2008
export COCOTB_RESOLVE_X=VALUE_ERROR

PWD=$(shell pwd)

export PYTHONPATH := $(PWD)/../python:$(PYTHONPATH)

VHDL_SOURCES = $(PWD)/../firmware/l1calogfex_pkg.vhd
VHDL_SOURCES += $(PWD)/../firmware/l1calogfex_address_decoder.vhd

export BACKANNOTATED_YAML := $(PWD)/../firmware/l1calogfex_backannotated.yaml

TOPLEVEL := l1calogfex_address_decoder
MODULE   := rtl_simulation

include $(shell cocotb-config --makefiles)/Makefile.sim
