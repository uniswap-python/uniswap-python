import os
from decimal import Decimal

from colorama import Fore, Style
from web3 import Web3

from uniswap import Uniswap4, V4pools
from uniswap.types import PoolKey


def pool_tests():
    # pool list tests
    first_block = 21688329
    print("Testing fetch_poolkey_data()...")
    try:
        v4pools_test.fetch_poolkey_data(first_block, chunk_size=500, clear_list=False)
        print("Test passed.")
    except Exception as e:
        print(f"Test failed. {e}")

    print("Testing save_poolkeys_list() absolute path")
    try:
        v4pools_test.save_poolkeys_list(
            os.path.join(_TESTS_DIR, "pools", "pool_list_mainnet.tst1")
        )
        print("Test passed.")
    except Exception as e:
        print(f"Test failed. {e}")

    print("Testing load_poolkeys_list() absolute path")
    try:
        v4pools_test.load_poolkeys_list(
            os.path.join(_TESTS_DIR, "pools", "pool_list_mainnet.tst1")
        )
        print("Test passed.")
    except Exception as e:
        print(f"Test failed. {e}")

    print("Testing get_pool_key() for ETH-USDC (correct entry)...")
    test_result = v4pools_test.get_poolkeys_sublist(
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "0x0000000000000000000000000000000000000000",
    )
    print(test_result)
    if len(test_result) > 0:
        print("Test passed.")
    else:
        print("Test failed.")

    print("Testing get_pool_key() for 0x1-WETH (incorrect entry)")
    test_result = v4pools_test.get_poolkeys_sublist(
        "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "0x0000000000000000000000000000000000000001",
    )
    print(test_result)
    if len(test_result) == 0:
        print("Test passed.")
    else:
        print("Test failed.")

    print()
    print()


def quoter_tests():
    # price functions tests

    # get_token_token_spot_price() tests
    print(f"Testing getSlot0() for {Fore.GREEN}ETH-USDC{Style.RESET_ALL}")
    test_result = str(uniV4_test.get_token_token_spot_price(test_ETH, test_USDC))
    print(f"Result: {Fore.GREEN}" + test_result + f"{Style.RESET_ALL}")

    print(f"Testing getSlot0() for {Fore.GREEN}USDC-ETH{Style.RESET_ALL}")
    test_result = str(uniV4_test.get_token_token_spot_price(test_USDC, test_ETH))
    print(f"Result: {Fore.GREEN}" + test_result + f"{Style.RESET_ALL}")
    print()
    print()

    test_pool_key1 = PoolKey(
        test_ETH,
        test_USDC,
        default_test_fee,
        default_test_tick_spacing,
        default_test_hooks,
    )
    test_pool_key2 = PoolKey(
        test_USDT,
        test_USDC,
        test_pool2_fee,
        test_pool2_tick_spacing,
        default_test_hooks,
    )
    test_path_1hop = list()
    test_path_1hop.append(test_pool_key1)
    test_path_2hop = list()
    test_path_2hop.append(test_pool_key1)
    test_path_2hop.append(test_pool_key2)

    # Testing get_quote_exact_input_single()
    test_volume = 1
    print(
        "Testing exactInputSingle() for "
        + str(test_volume)
        + f" {Fore.GREEN}ETH{Style.RESET_ALL} to {Fore.GREEN}USDC{Style.RESET_ALL}"
    )
    test_result = str(
        uniV4_test.get_quote_exact_input_single(
            test_ETH,
            test_USDC,
            test_volume * test_d0,
            default_test_fee,
            default_test_tick_spacing,
        )
        / test_d1
    )
    test_result_alt = str(
        uniV4_test.get_price_input(
            test_ETH,
            test_USDC,
            test_volume * test_d0,
            default_test_fee,
            default_test_tick_spacing,
        )
        / test_d1
    )
    print(
        f"Result: {Fore.GREEN}"
        + test_result
        + " / "
        + test_result_alt
        + f"{Style.RESET_ALL} USDC"
    )

    test_volume = 3000
    print(
        "Testing exactInputSingle() for "
        + str(test_volume)
        + f" {Fore.GREEN}USDC{Style.RESET_ALL} to {Fore.GREEN}ETH{Style.RESET_ALL}"
    )
    test_result = str(
        uniV4_test.get_quote_exact_input_single(
            test_USDC,
            test_ETH,
            test_volume * test_d1,
            default_test_fee,
            default_test_tick_spacing,
        )
        / test_d0
    )
    test_result_alt = str(
        uniV4_test.get_price_input(
            test_USDC,
            test_ETH,
            test_volume * test_d1,
            default_test_fee,
            default_test_tick_spacing,
        )
        / test_d0
    )
    print(
        f"Result: {Fore.GREEN}"
        + test_result
        + " / "
        + test_result_alt
        + f"{Style.RESET_ALL} ETH"
    )
    print()
    print()

    # Testing get_quote_exact_input()
    test_volume = 1
    print(
        "Testing exactInput() for "
        + str(test_volume)
        + f" {Fore.GREEN}ETH{Style.RESET_ALL} to {Fore.GREEN}USDC{Style.RESET_ALL}"
    )
    test_result = str(
        uniV4_test.get_quote_exact_input(
            test_ETH, test_volume * test_d0, test_path_1hop
        )
        / test_d1
    )
    test_result_alt = str(
        uniV4_test.get_price_input(
            test_ETH, test_USDC, test_volume * test_d0, route=test_path_1hop
        )
        / test_d1
    )
    print(
        f"Result: {Fore.GREEN}"
        + test_result
        + " / "
        + test_result_alt
        + f"{Style.RESET_ALL} USDC"
    )

    test_volume = 3000
    print(
        "Testing exactInput() for "
        + str(test_volume)
        + f" {Fore.GREEN}USDC{Style.RESET_ALL} to {Fore.GREEN}ETH{Style.RESET_ALL}"
    )
    test_result = str(
        uniV4_test.get_quote_exact_input(
            test_USDC, test_volume * test_d1, test_path_1hop
        )
        / test_d0
    )
    test_result_alt = str(
        uniV4_test.get_price_input(
            test_USDC, test_ETH, test_volume * test_d1, route=test_path_1hop
        )
        / test_d0
    )
    print(
        f"Result: {Fore.GREEN}"
        + test_result
        + " / "
        + test_result_alt
        + f"{Style.RESET_ALL} ETH"
    )

    # 2-hop test
    test_volume = 1
    print(
        "Testing 2-hop exactInput() for "
        + str(test_volume)
        + f" {Fore.GREEN}ETH{Style.RESET_ALL} to {Fore.GREEN}USDT{Style.RESET_ALL}"
    )
    test_result = str(
        uniV4_test.get_quote_exact_input(
            test_ETH, test_volume * test_d0, test_path_2hop
        )
        / test_d2
    )
    test_result_alt = str(
        uniV4_test.get_price_input(
            test_ETH, test_USDT, test_volume * test_d0, route=test_path_2hop
        )
        / test_d2
    )
    print(
        f"Result: {Fore.GREEN}"
        + test_result
        + " / "
        + test_result_alt
        + f"{Style.RESET_ALL} USDT"
    )

    print()
    print()

    # Testing get_quote_exact_output_single()
    test_volume = 3000
    print(
        "Testing exactOutputSingle() for "
        + str(test_volume)
        + f" {Fore.GREEN}USDC{Style.RESET_ALL} to {Fore.GREEN}ETH{Style.RESET_ALL}"
    )
    test_result = str(
        uniV4_test.get_quote_exact_output_single(
            test_ETH,
            test_USDC,
            test_volume * test_d1,
            default_test_fee,
            default_test_tick_spacing,
        )
        / test_d0
    )
    test_result_alt = str(
        uniV4_test.get_price_output(
            test_ETH,
            test_USDC,
            test_volume * test_d1,
            default_test_fee,
            default_test_tick_spacing,
        )
        / test_d0
    )
    print(
        f"Result: {Fore.GREEN}"
        + test_result
        + " / "
        + test_result_alt
        + f"{Style.RESET_ALL} ETH"
    )

    test_volume = 1
    print(
        "Testing exactOutputSingle() for "
        + str(test_volume)
        + f" {Fore.GREEN}ETH{Style.RESET_ALL} to {Fore.GREEN}USDC{Style.RESET_ALL}"
    )
    test_result = str(
        uniV4_test.get_quote_exact_output_single(
            test_USDC,
            test_ETH,
            test_volume * test_d0,
            default_test_fee,
            default_test_tick_spacing,
        )
        / test_d1
    )
    test_result_alt = str(
        uniV4_test.get_price_output(
            test_USDC,
            test_ETH,
            test_volume * test_d0,
            default_test_fee,
            default_test_tick_spacing,
        )
        / test_d1
    )
    print(
        f"Result: {Fore.GREEN}"
        + test_result
        + " / "
        + test_result_alt
        + f"{Style.RESET_ALL} USDC"
    )

    # Testing get_quote_exact_output()
    test_volume = 3000
    print(
        "Testing exactOutput() one hop for "
        + str(test_volume)
        + f" {Fore.GREEN}USDC{Style.RESET_ALL} to {Fore.GREEN}ETH{Style.RESET_ALL}"
    )
    test_result = str(
        uniV4_test.get_quote_exact_output(
            test_USDC, test_volume * test_d1, test_path_1hop
        )
        / test_d0
    )
    test_result_alt = str(
        uniV4_test.get_price_output(
            test_USDC, test_ETH, test_volume * test_d1, route=test_path_1hop
        )
        / test_d0
    )
    print(
        f"Result: {Fore.GREEN}"
        + test_result
        + " / "
        + test_result_alt
        + f"{Style.RESET_ALL} ETH"
    )

    test_volume = 1
    print(
        "Testing exactOutput() for "
        + str(test_volume)
        + f" {Fore.GREEN}ETH{Style.RESET_ALL} to {Fore.GREEN}USDC{Style.RESET_ALL}"
    )
    test_result = str(
        uniV4_test.get_quote_exact_output(
            test_ETH, test_volume * test_d0, test_path_1hop
        )
        / test_d1
    )
    test_result_alt = str(
        uniV4_test.get_price_output(
            test_ETH, test_USDC, test_volume * test_d0, route=test_path_1hop
        )
        / test_d1
    )
    print(
        f"Result: {Fore.GREEN}"
        + test_result
        + " / "
        + test_result_alt
        + f"{Style.RESET_ALL} USDC"
    )

    # 2-hop test
    test_volume = 1
    print(
        "Testing 2-hop exactOutput() for "
        + str(test_volume)
        + f" {Fore.GREEN}ETH{Style.RESET_ALL} to {Fore.GREEN}USDT{Style.RESET_ALL}"
    )
    reversed_test_path_2hop = list(reversed(test_path_2hop))
    test_result = str(
        uniV4_test.get_quote_exact_output(
            test_ETH, test_volume * test_d0, reversed_test_path_2hop
        )
        / test_d2
    )
    test_result_alt = str(
        uniV4_test.get_price_output(
            test_ETH, test_USDT, test_volume * test_d0, route=reversed_test_path_2hop
        )
        / test_d2
    )

    print(
        f"Result: {Fore.GREEN}"
        + test_result
        + " / "
        + test_result_alt
        + f"{Style.RESET_ALL} USDT"
    )

    print()
    print()


def price_impact_tests():
    ##estimate_price_impact() tests
    test_volume = 1
    print(
        "Testing estimate_price_impact() for "
        + str(test_volume)
        + f" {Fore.GREEN}ETH{Style.RESET_ALL} to {Fore.GREEN}USDC{Style.RESET_ALL}"
    )
    test_result = str(
        uniV4_test.estimate_price_impact(test_ETH, test_USDC, test_volume * test_d0)
    )
    print(f"Result: {Fore.GREEN}" + test_result + f"{Style.RESET_ALL} %")
    test_volume = 10
    print(
        "Testing estimate_price_impact() for "
        + str(test_volume)
        + f" {Fore.GREEN}ETH{Style.RESET_ALL} to {Fore.GREEN}USDC{Style.RESET_ALL}"
    )
    test_result = str(
        uniV4_test.estimate_price_impact(test_ETH, test_USDC, test_volume * test_d0)
    )
    print(f"Result: {Fore.GREEN}" + test_result + f"{Style.RESET_ALL} %")
    test_volume = 100
    print(
        "Testing estimate_price_impact() for "
        + str(test_volume)
        + f" {Fore.GREEN}ETH{Style.RESET_ALL} to {Fore.GREEN}USDC{Style.RESET_ALL}"
    )
    test_result = str(
        uniV4_test.estimate_price_impact(test_ETH, test_USDC, test_volume * test_d0)
    )
    print(f"Result: {Fore.GREEN}" + test_result + f"{Style.RESET_ALL} %")
    test_volume = 1000
    print(
        "Testing estimate_price_impact() for "
        + str(test_volume)
        + f" {Fore.GREEN}ETH{Style.RESET_ALL} to {Fore.GREEN}USDC{Style.RESET_ALL}"
    )
    test_result = str(
        uniV4_test.estimate_price_impact(test_ETH, test_USDC, test_volume * test_d0)
    )
    print(f"Result: {Fore.GREEN}" + test_result + f"{Style.RESET_ALL} %")

    print()
    print()


def state_view_tests():
    ##StateView tests
    # get_liquidity() test
    print(
        f"Testing get_liquidity() for ({Fore.GREEN}ETH{Style.RESET_ALL}, {Fore.GREEN}USDC{Style.RESET_ALL}) liquidity pool"
    )
    test_result = uniV4_test.stateview_get_liquidity(
        test_ETH,
        test_USDC,
        default_test_fee,
        default_test_tick_spacing,
        default_test_hooks,
    )
    print(f"Result: {Fore.GREEN}" + str(test_result) + f"{Style.RESET_ALL}")
    # get_slot0() test
    print(
        f"Testing get_slot0() for ({Fore.GREEN}ETH{Style.RESET_ALL}, {Fore.GREEN}USDC{Style.RESET_ALL}) liquidity pool"
    )
    test_result1 = uniV4_test.stateview_get_slot0(
        test_ETH,
        test_USDC,
        default_test_fee,
        default_test_tick_spacing,
        default_test_hooks,
    )
    test_tick: int = int(test_result1["tick"])
    print(f"Result: {Fore.GREEN}" + str(test_result1) + f"{Style.RESET_ALL}")
    # get_fee_growth_globals() test
    print(
        f"Testing get_fee_growth_globals() for ({Fore.GREEN}ETH{Style.RESET_ALL}, {Fore.GREEN}USDC{Style.RESET_ALL}) liquidity pool"
    )
    test_result2 = uniV4_test.stateview_get_fee_growth_globals(
        test_ETH,
        test_USDC,
        default_test_fee,
        default_test_tick_spacing,
        default_test_hooks,
    )
    print(f"Result: {Fore.GREEN}" + str(test_result2) + f"{Style.RESET_ALL}")
    # get_fee_growth_inside() test
    print(
        f"Testing get_fee_growth_inside() for ({Fore.GREEN}ETH{Style.RESET_ALL}, {Fore.GREEN}USDC{Style.RESET_ALL}) liquidity pool"
    )
    test_result3 = uniV4_test.stateview_get_fee_growth_inside(
        test_ETH,
        test_USDC,
        default_test_fee,
        default_test_tick_spacing,
        default_test_hooks,
        test_tick - default_test_tick_spacing * 3,
        test_tick + default_test_tick_spacing * 3,
    )
    print(f"Result: {Fore.GREEN}" + str(test_result3) + f"{Style.RESET_ALL}")
    #
    # get_position_info_stateview() test
    print(
        f"Testing get_position_info_stateview() for ({Fore.GREEN}ETH{Style.RESET_ALL}, {Fore.GREEN}USDC{Style.RESET_ALL}) liquidity pool"
    )
    # taken from 0xe529044f9cb8526c9b4d635f81889d991d217a6fb859b3e4f446cbe0ba988e31 as sample data
    pos_inf_token0 = "0x6c76de483f1752ac8473e2b4983a873991e70da7"
    pos_inf_token1 = "0xdac17f958d2ee523a2206206994597c13d831ec7"
    pos_inf_fee = 13686
    pos_inf_tick_spacing = 10
    pos_inf_hooks = default_test_hooks
    pos_inf_owner = "0x42562F062D618EfeB53cAB346E3b6E2EaB2e5BCB"
    pos_inf_tick_lower = -301070
    pos_inf_tick_upper = -292859
    pos_inf_token_id = 156881
    test_result4 = uniV4_test.stateview_get_position_info(
        pos_inf_token0,
        pos_inf_token1,
        pos_inf_fee,
        pos_inf_tick_spacing,
        pos_inf_hooks,
        pos_inf_owner,
        pos_inf_tick_lower,
        pos_inf_tick_upper,
        pos_inf_token_id,
    )
    print(f"Result: {Fore.GREEN}" + str(test_result4) + f"{Style.RESET_ALL}")
    # get_tick_bitmap_stateview() test
    print(
        f"Testing get_tick_bitmap()_stateview() for ({Fore.GREEN}ETH{Style.RESET_ALL}, {Fore.GREEN}USDC{Style.RESET_ALL}) liquidity pool"
    )
    test_result5 = uniV4_test.stateview_get_tick_bitmap(
        test_ETH,
        test_USDC,
        default_test_fee,
        default_test_tick_spacing,
        default_test_hooks,
        -30000,  # must be int16
    )
    print(f"Result: {Fore.GREEN}" + str(test_result5) + f"{Style.RESET_ALL}")
    # get_tick_fee_growth_outside_stateview() test
    print(
        f"Testing get_tick_fee_growth_outside()_stateview() for ({Fore.GREEN}ETH{Style.RESET_ALL}, {Fore.GREEN}USDC{Style.RESET_ALL}) liquidity pool"
    )
    test_result6 = uniV4_test.stateview_get_tick_fee_growth_outside(
        test_ETH,
        test_USDC,
        default_test_fee,
        default_test_tick_spacing,
        default_test_hooks,
        test_tick,
    )
    print(f"Result: {Fore.GREEN}" + str(test_result6) + f"{Style.RESET_ALL}")
    # get_tick_pool_info_stateview() test
    print(
        f"Testing get_tick_pool_info()_stateview() for ({Fore.GREEN}ETH{Style.RESET_ALL}, {Fore.GREEN}USDC{Style.RESET_ALL}) liquidity pool"
    )
    test_result7 = uniV4_test.stateview_get_tick_pool_info(
        test_ETH,
        test_USDC,
        default_test_fee,
        default_test_tick_spacing,
        default_test_hooks,
        test_tick,
    )
    print(f"Result: {Fore.GREEN}" + str(test_result7) + f"{Style.RESET_ALL}")
    print()
    print()


def swap_tests():
    # swap functions tests

    test_pool_key1 = PoolKey(
        test_ETH,
        test_USDC,
        default_test_fee,
        default_test_tick_spacing,
        default_test_hooks,
    )
    test_pool_key2 = PoolKey(
        test_USDT,
        test_USDC,
        test_pool2_fee,
        test_pool2_tick_spacing,
        default_test_hooks,
    )
    test_path_1hop = list()
    test_path_1hop.append(test_pool_key1)
    test_path_2hop = list()
    test_path_2hop.append(test_pool_key1)
    test_path_2hop.append(test_pool_key2)

    # Testing make_swap_input(), single hop, token0 is ETH
    test_volume_in = 1
    print(
        "Testing make_swap_input() for "
        + str(test_volume_in)
        + f" {Fore.GREEN}ETH{Style.RESET_ALL} to {Fore.GREEN}USDC{Style.RESET_ALL}, single hop"
    )
    test_volume_out = uniV4_test.get_price_input(
        test_ETH,
        test_USDC,
        test_volume_in * test_d0,
        test_pool_key1.fee,
        test_pool_key1.tick_spacing,
        test_pool_key1.hooks,
    )
    test_volume_out_min: int = int(
        test_volume_out * Decimal(1 - uniV4_test.max_slippage)
    )

    test_result = uniV4_test.make_swap_input(
        test_ETH,
        test_USDC,
        test_volume_in * test_d0,
        test_volume_out_min,
        test_pool_key1,
    )
    print(f"Result: {Fore.GREEN}" + test_result.hex() + f"{Style.RESET_ALL}")

    # Testing make_swap_input(), single hop, token0 is non-ETH
    test_volume_in = 1
    print(
        "Testing make_swap_input() for "
        + str(test_volume_in)
        + f" {Fore.GREEN}USDC{Style.RESET_ALL} to {Fore.GREEN}ETH{Style.RESET_ALL}, single hop"
    )
    test_volume_out = uniV4_test.get_price_input(
        test_USDC,
        test_ETH,
        test_volume_in * test_d1,
        test_pool_key1.fee,
        test_pool_key1.tick_spacing,
        test_pool_key1.hooks,
    )
    test_volume_out_min = int(test_volume_out * Decimal(1 - uniV4_test.max_slippage))

    test_result = uniV4_test.make_swap_input(
        test_USDC,
        test_ETH,
        test_volume_in * test_d1,
        test_volume_out_min,
        test_pool_key1,
    )
    print(f"Result: {Fore.GREEN}" + test_result.hex() + f"{Style.RESET_ALL}")
    print()
    print()

    # Testing make_swap_input(), 2-hop test, token0 is ETH
    test_volume_in = 1
    print(
        "Testing 2-hop make_swap_input() for "
        + str(test_volume_in)
        + f" {Fore.GREEN}ETH{Style.RESET_ALL} to {Fore.GREEN}USDT{Style.RESET_ALL}, 2-hop"
    )
    test_volume_out = uniV4_test.get_price_input(
        test_ETH, test_USDT, test_volume_in * test_d0, route=test_path_2hop
    )
    test_volume_out_min = int(test_volume_out * Decimal(1 - uniV4_test.max_slippage))

    test_result = uniV4_test.make_swap_input(
        test_ETH,
        test_USDT,
        test_volume_in * test_d0,
        test_volume_out_min,
        route=test_path_2hop,
    )
    print(f"Result: {Fore.GREEN}" + test_result.hex() + f"{Style.RESET_ALL}")

    # Testing make_swap_input(), 2-hop test, token0 is non-ETH
    test_volume_in = 1
    print(
        "Testing 2-hop make_swap_input() for "
        + str(test_volume_in)
        + f" {Fore.GREEN}USDT{Style.RESET_ALL} to {Fore.GREEN}ETH{Style.RESET_ALL}, 2-hop"
    )
    test_volume_out = uniV4_test.get_price_input(
        test_USDT,
        test_ETH,
        test_volume_in * test_d1,
        route=list(reversed(test_path_2hop)),
    )
    test_volume_out_min = int(test_volume_out * Decimal(1 - uniV4_test.max_slippage))
    test_result = uniV4_test.make_swap_input(
        test_USDT,
        test_ETH,
        test_volume_in * test_d1,
        test_volume_out_min,
        route=list(reversed(test_path_2hop)),
    )
    print(f"Result: {Fore.GREEN}" + test_result.hex() + f"{Style.RESET_ALL}")

    print()
    print()

    # Testing make_swap_output(), single hop, token0 is ETH
    test_volume_out = 1
    print(
        "Testing make_swap_output() for "
        + str(test_volume_out)
        + f" {Fore.GREEN}USDC{Style.RESET_ALL} to {Fore.GREEN}ETH{Style.RESET_ALL}, single hop"
    )
    test_volume_in = uniV4_test.get_price_output(
        test_ETH,
        test_USDC,
        test_volume_out * test_d1,
        test_pool_key1.fee,
        test_pool_key1.tick_spacing,
    )
    test_volume_in_max = int(test_volume_in * Decimal(1 + uniV4_test.max_slippage))
    test_result = uniV4_test.make_swap_output(
        test_ETH,
        test_USDC,
        test_volume_out * test_d1,
        test_volume_in_max,
        test_pool_key1,
    )
    print(f"Result: {Fore.GREEN}" + test_result.hex() + f"{Style.RESET_ALL}")

    # Testing make_swap_output(), single hop, token0 is non-ETH
    test_volume_out = 1
    print(
        "Testing make_swap_output() for "
        + str(test_volume_out)
        + f" {Fore.GREEN}ETH{Style.RESET_ALL} to {Fore.GREEN}USDC{Style.RESET_ALL}, single hop"
    )
    test_volume_in = uniV4_test.get_price_output(
        test_USDC,
        test_ETH,
        test_volume_out * test_d1,
        test_pool_key1.fee,
        test_pool_key1.tick_spacing,
    )
    test_volume_in_max = int(test_volume_in * Decimal(1 + uniV4_test.max_slippage))
    test_result = uniV4_test.make_swap_output(
        test_USDC,
        test_ETH,
        test_volume_out * test_d1,
        test_volume_in_max,
        test_pool_key1,
    )
    print(f"Result: {Fore.GREEN}" + test_result.hex() + f"{Style.RESET_ALL}")

    # Testing make_swap_output(), 2-hop, token0 is ETH
    test_volume_out = 1
    print(
        "Testing 2-hop exactOutput() for "
        + str(test_volume_out)
        + f" {Fore.GREEN}ETH{Style.RESET_ALL} to {Fore.GREEN}USDT{Style.RESET_ALL}, 2-hop"
    )
    reversed_test_path_2hop = list(reversed(test_path_2hop))
    test_volume_in = uniV4_test.get_price_output(
        test_ETH, test_USDT, test_volume_out * test_d0, route=reversed_test_path_2hop
    )
    test_volume_in_max = int(test_volume_in * Decimal(1 + uniV4_test.max_slippage))
    test_result = uniV4_test.make_swap_output(
        test_ETH,
        test_USDT,
        test_volume_out * test_d2,
        test_volume_in_max,
        route=reversed_test_path_2hop,
    )

    print(f"Result: {Fore.GREEN}" + test_result.hex() + f"{Style.RESET_ALL}")

    # Testing make_swap_output(), 2-hop, token0 is non-ETH
    test_volume_out = 1
    print(
        "Testing 2-hop exactOutput() for "
        + str(test_volume_out)
        + f" {Fore.GREEN}USDT{Style.RESET_ALL} to {Fore.GREEN}ETH{Style.RESET_ALL}, 2-hop"
    )
    test_volume_in = uniV4_test.get_price_output(
        test_USDT, test_ETH, test_volume_out * test_d0, route=test_path_2hop
    )
    test_volume_in_max = int(test_volume_in * Decimal(1 + uniV4_test.max_slippage))

    test_result = uniV4_test.make_swap_output(
        test_USDT,
        test_ETH,
        test_volume_out * test_d2,
        test_volume_in_max,
        route=test_path_2hop,
    )

    print(f"Result: {Fore.GREEN}" + test_result.hex() + f"{Style.RESET_ALL}")

    print()
    print()


def liquidity_tests():
    ##liquidity management functions tests
    # get_position_info() test
    test_token_id: int = 1
    print(
        f"Testing get_position_info() for token ID {Fore.GREEN}{test_token_id} {Style.RESET_ALL}"
    )
    test_result1 = uniV4_test.get_position_info(test_token_id)
    test_pool_id_result: int = int.from_bytes(test_result1["poolID"], byteorder="big")
    test_pool_id_check = uniV4_test.get_pool_id(
        PoolKey(
            test_result1["currency0"],
            test_result1["currency1"],
            test_result1["fee"],
            test_result1["tickSpacing"],
            test_result1["hooks"],
        )
    )
    print(
        "Result: "
        + str(test_result1)
        + f"; truncated pool ID: {Fore.GREEN}"
        + hex(test_pool_id_result)
        + f"{Style.RESET_ALL}"
        + f"; full pool ID: {Fore.GREEN}"
        + f"{test_pool_id_check.hex()}"
        + f"{Style.RESET_ALL}"
    )
    print()
    print()

    # get_position_info() test
    print(
        f"Testing get_position_value() for token ID {Fore.GREEN}{test_token_id} {Style.RESET_ALL}"
    )
    test_result1 = uniV4_test.get_position_value(test_token_id, 18, 6)
    print("Result: " + str(test_result1))
    print()
    print()

    test_token_id = 206788
    print(
        f"Testing get_position_info() for token ID {Fore.GREEN}{test_token_id} {Style.RESET_ALL}"
    )
    test_result1 = uniV4_test.get_position_value(test_token_id, 18, 8)
    print("Result: " + str(test_result1))
    print()
    print()

    test_transaction_hash: str = (
        "0xb30d3dde98f715e5880da9f8833f99823623229e193e04661cb7ce193e4028f8"
    )

    print(
        f"Testing get_minted_token_id() for transaction {Fore.GREEN}{test_transaction_hash} {Style.RESET_ALL}"
    )
    test_result_token_id = uniV4_test.get_minted_token_id(test_transaction_hash)
    print("Result: " + str(test_result_token_id))
    print()
    print()

    test_transaction_hash = (
        "0xfe0389d167acbe1bb10f2ef0487ae123beab8a5b334799d68632957e3d16ff6e"
    )

    print(
        f"Testing get_minted_token_id() for transaction {Fore.GREEN}{test_transaction_hash} {Style.RESET_ALL}"
    )
    test_result_token_id = uniV4_test.get_minted_token_id(test_transaction_hash)
    print("Result: " + str(test_result_token_id))
    print()
    print()


def reserves_lens_tests():
    ##reserves lens tests
    print(
        f"Testing reserves_lens_get_pool_tvl() for ({Fore.GREEN}ETH{Style.RESET_ALL}, {Fore.GREEN}USDC{Style.RESET_ALL}) liquidity pool"
    )
    test_result = uniV4_test.reserves_lens_get_pool_tvl(
        PoolKey(
            test_ETH,
            test_USDC,
            default_test_fee,
            default_test_tick_spacing,
            default_test_hooks,
        )
    )

    print("Result: " + str(test_result))
    print()
    print()


if __name__ == "__main__":
    test_ETH = "0x0000000000000000000000000000000000000000"
    test_USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    test_USDT = Web3.to_checksum_address("0xdac17f958d2ee523a2206206994597c13d831ec7")
    test_zero_hook = "0x0000000000000000000000000000000000000000"
    test_d0 = 10**18
    test_d1 = 10**6
    test_d2 = 10**6
    test_fee = 500
    default_test_fee = 500
    default_test_tick_spacing = 10
    test_pool2_fee = 10
    test_pool2_tick_spacing = 1
    default_test_hooks = test_zero_hook
    _TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

    rpc_endpoint = "https://eth.drpc.org"
    address = "0x94e3361495bD110114ac0b6e35Ed75E77E6a6cFA"
    w3_test = Web3(Web3.HTTPProvider(rpc_endpoint, request_kwargs={"timeout": 60}))

    uniV4_test = Uniswap4(
        address,
        None,
        provider=rpc_endpoint,
    )
    v4pools_test = V4pools(w3_test)

    ##TESTS
    print("Started.")
    print()
    print()

    # pool_tests()
    quoter_tests()
    price_impact_tests()
    state_view_tests()
    liquidity_tests()
    reserves_lens_tests()
    # swap_tests()

    print("Done.")
