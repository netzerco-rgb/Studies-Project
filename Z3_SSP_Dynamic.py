import argparse
import sys
from typing import Dict, List, Sequence, Set, Tuple

from z3 import (
    And,
    Bool,
    BoolVal,
    BoolRef,
    If,
    Int,
    IntNumRef,
    ModelRef,
    Not,
    Or,
    Solver,
    sat,
)


# constants
DOWN = 0
DIAG = 1
SPLIT = 0
PASS = 1


# ssp calculations:
# validates that SSP input is not empty and has only positive integers
def validate_elements(elements: Sequence[int]) -> None:
    if not elements:
        raise ValueError(
            "Error: At least one subset-sum element must be provided."
        )

    if any(element <= 0 for element in elements):
        raise ValueError(
            "Error: All subset-sum elements must be positive integers."
        )

# calculates: split rows
def calculate_split_rows(elements: Sequence[int]) -> List[int]:
    split_rows = []
    current_sum = 0

    for element in elements:
        current_sum += element
        split_rows.append(current_sum)

    return split_rows

# calculates: possible subset sums
def calculate_valid_sums(elements: Sequence[int]) -> Set[int]:
    valid_sums = {0}

    for element in elements:
        new_sums = {
            current_sum + element
            for current_sum in valid_sums
        }
        valid_sums.update(new_sums)

    return valid_sums

# calculates: not valid subset sums
def calculate_invalid_sums(
    max_sum: int,
    valid_sums: Set[int],
) -> Set[int]:
    all_columns = set(range(max_sum + 1))
    return all_columns - valid_sums


# Z3 expressions
def values_expression(variable, values: Sequence[int]) -> BoolRef:
    if not values:
        return BoolVal(False)

    return Or(*[variable == value for value in values])
# split rows
def is_split_row_expr(row, split_rows: Sequence[int]) -> BoolRef:
    return values_expression(row, split_rows)
# sum
def is_sum_col_expr(column, valid_sums: Set[int]) -> BoolRef:
    return values_expression(column, sorted(valid_sums))
# xsum
def is_xsum_col_expr(column, invalid_sums: Set[int]) -> BoolRef:
    return values_expression(column, sorted(invalid_sums))

# Z3 synamic model for SSP
def build_model(
    elements: Sequence[int],
    path_len: int | None = None,
    tracked_points: Sequence[Tuple[int, int]] | None = None,
):
    # 1. input validation: elements must be a non-empty list of positive integers
    validate_elements(elements)

    # 2. calculating the maximum sum
    max_sum = sum(elements)

    # 3. calculating split rows (cumulative Sum)
    split_rows = calculate_split_rows(elements)

    # 4. calculating all possible valid subset sums
    valid_sums = calculate_valid_sums(elements)
    ## TEST ONLY: pretend that 7 is not a valid subset sum ##
    #valid_sums.discard(7)

    # 5. calculating all invalid subset sums
    invalid_sums = calculate_invalid_sums(max_sum, valid_sums)

    if path_len is None:
        path_len = max_sum

    if path_len < 0:
        raise ValueError("Error: path_len cannot be negative.")

    if tracked_points is None:
        tracked_points = []

    solver = Solver()

    # state variables
    row = [
        Int(f"row_{time}")
        for time in range(path_len + 1)
    ]
    column = [
        Int(f"column_{time}")
        for time in range(path_len + 1)
    ]
    direction = [
        Int(f"direction_{time}")
        for time in range(path_len + 1)
    ]
    junction = [
        Int(f"junction_{time}")
        for time in range(path_len + 1)
    ]

    # visites Variables
    visited: Dict[Tuple[int, int], List[BoolRef]] = {}

    for tracked_row, tracked_column in tracked_points:
        visited[(tracked_row, tracked_column)] = [
            Bool(
                f"visited_{tracked_row}_{tracked_column}_{time}"
            )
            for time in range(path_len + 1)
        ]

    # value constrains
    for time in range(path_len + 1):
        solver.add(
            row[time] >= 0,
            row[time] <= max_sum,
        )

        solver.add(
            column[time] >= 0,
            column[time] <= max_sum,
        )

        solver.add(
            Or(
                direction[time] == DOWN,
                direction[time] == DIAG,
            )
        )

        solver.add(
            Or(
                junction[time] == SPLIT,
                junction[time] == PASS,
            )
        )

    # initial state
    solver.add(row[0] == 0)
    solver.add(column[0] == 0)
    solver.add(direction[0] == DOWN)
    solver.add(junction[0] == SPLIT)

    for point_variables in visited.values():
        solver.add(point_variables[0] == False)

    # transitions
    for time in range(path_len):

        current_row = row[time]
        next_row = row[time + 1]

        current_column = column[time]
        next_column = column[time + 1]

        current_direction = direction[time]
        next_direction = direction[time + 1]

        current_junction = junction[time]
        next_junction = junction[time + 1]

        # next row
        solver.add(
            next_row == If(
                current_row == max_sum,
                0,
                current_row + 1,
            )
        )

        # next direction
        solver.add(
            If(
                current_row == max_sum,

                # Restart direction
                next_direction == DOWN,

                If(
                    current_junction == SPLIT,

                    # at a split: choose nondeterministically
                    Or(
                        next_direction == DOWN,
                        next_direction == DIAG,
                    ),

                    # at a pass junction: preserve direction
                    next_direction == current_direction,
                ),
            )
        )

        # next column
        next_column_expression = If(
            current_row == max_sum,

            # reset after completing the path
            0,

            If(
                And(
                    current_junction == SPLIT,
                    next_direction == DOWN,
                ),

                current_column,

                If(
                    And(
                        current_junction == SPLIT,
                        next_direction == DIAG,
                    ),

                    If(
                        current_column < max_sum,
                        current_column + 1,
                        0,
                    ),

                    If(
                        And(
                            current_junction == PASS,
                            current_direction == DOWN,
                        ),

                        current_column,

                        If(
                            And(
                                current_junction == PASS,
                                current_direction == DIAG,
                            ),

                            If(
                                current_column < max_sum,
                                current_column + 1,
                                0,
                            ),

                            current_column,
                        ),
                    ),
                ),
            ),
        )

        solver.add(next_column == next_column_expression)

        # next junction

        solver.add(
            next_junction == If(
                current_row == max_sum,

                SPLIT,

                If(
                    is_split_row_expr(
                        next_row,
                        split_rows,
                    ),
                    SPLIT,
                    PASS,
                ),
            )
        )

        # visited rows
        for point, point_variables in visited.items():
            tracked_row, tracked_column = point

            reached_point = And(
                next_row == tracked_row,
                next_column == tracked_column,
                next_direction == DIAG,
            )

            solver.add(
                point_variables[time + 1] == If(
                    current_row == max_sum,

                    # reset when a computation finishes
                    False,

                    # otherwise keep the old value
                    Or(
                        point_variables[time],
                        reached_point,
                    ),
                )
            )

    model_data = {
        "max_sum": max_sum,
        "split_rows": split_rows,
        "valid_sums": valid_sums,
        "invalid_sums": invalid_sums,
        "path_len": path_len,
        "row": row,
        "column": column,
        "direction": direction,
        "junction": junction,
        "visited": visited,
    }

    return solver, model_data


# trace printing

def z3_int(model: ModelRef, expression) -> int:
    # checks Z3 int expression and returns a Python integer
    value = model.evaluate(expression, model_completion=True)

    if not isinstance(value, IntNumRef):
        raise ValueError(f"Expected integer value, received: {value}")

    return value.as_long()


def print_trace(
    model: ModelRef,
    model_data: dict,
    final_time: int,
) -> None:
    row = model_data["row"]
    column = model_data["column"]
    direction = model_data["direction"]
    junction = model_data["junction"]
    visited = model_data["visited"]

    print("Counterexample trace:")

    for time in range(final_time + 1):
        row_value = z3_int(model, row[time])
        column_value = z3_int(model, column[time])
        direction_value = z3_int(model, direction[time])
        junction_value = z3_int(model, junction[time])

        direction_text = (
            "down"
            if direction_value == DOWN
            else "diag"
        )

        junction_text = (
            "split"
            if junction_value == SPLIT
            else "pass"
        )

        trace_line = (
            f"t={time:2d}: "
            f"row={row_value:2d}, "
            f"column={column_value:2d}, "
            f"direction={direction_text:4s}, "
            f"junction={junction_text:5s}"
        )

        for point, point_variables in visited.items():
            point_value = model.evaluate(
                point_variables[time],
                model_completion=True,
            )

            trace_line += f", visited{point}={point_value}"

        print(trace_line)


# checks if satisfied:
    # SAT: A bad path exists
    # UNSAT: No bad complete path exists
def check_always_right_path(
    elements: Sequence[int],
    tracked_points: Sequence[Tuple[int, int]] | None = None,
) -> bool:

    solver, model_data = build_model(
        elements=elements,
        path_len=sum(elements),
        tracked_points=tracked_points,
    )

    max_sum = model_data["max_sum"]
    final_time = model_data["path_len"]

    row = model_data["row"]
    column = model_data["column"]

    valid_sums = model_data["valid_sums"]
    invalid_sums = model_data["invalid_sums"]

    # checks for: here exists a complete path that ends in an invalid column
    bad_final_state = And(
        row[final_time] == max_sum,
        Not(
            is_sum_col_expr(
                column[final_time],
                valid_sums,
            )
        ),
    )

    solver.add(bad_final_state)

    # display calculated values
    print(f"Elements:       {list(elements)}")
    print(f"Maximum sum:   {max_sum}")
    print(f"Split rows:    {model_data['split_rows']}")
    print(f"Valid sums:    {sorted(valid_sums)}")
    print(f"Invalid sums:  {sorted(invalid_sums)}")
    print(f"Path length:   {final_time}")


    # run Z3
    # 1. check if there exists a bad path
    result = solver.check()

    # 2. print results
    print(f"Z3 result: {result}")

    if result == sat:
        print(
            "Counterexample found: a complete computation ends at an invalid column."
        )

        model = solver.model()
        print_trace(model, model_data, final_time)

        return False

    print("No bad computation path exists.")
    print(
        "Therefore, every complete bounded path ends at a valid subset-sum column.\n"
    )

    return True


# converts command line from '3,1' into (3, 1)
def parse_tracked_point(value: str) -> Tuple[int, int]:

    try:
        row_text, column_text = value.split(",")
        tracked_row = int(row_text)
        tracked_column = int(column_text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Tracked points must use the format ROW,COLUMN, "
            "for example: 3,1"
        ) from error

    if tracked_row < 0 or tracked_column < 0:
        raise argparse.ArgumentTypeError(
            "Tracked row and column values cannot be negative."
        )

    return tracked_row, tracked_column


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Dynamic Subset Sum Problem model and verifier using Z3."
        )
    )

    # converts received integers into code elements
    parser.add_argument(
        "elements",
        metavar="N",
        type=int,
        nargs="+",
        help=(
            "Positive subset-sum elements separated by spaces. "
            "Example: 3 4 7"
        ),
    )

    # trace print specific pints:
        # each 2 elements will convey a point of (3,1) to see if the path has
        # already passed through this specific point
    parser.add_argument(
        "--track",
        metavar="ROW,COLUMN",
        type=parse_tracked_point,
        nargs="*",
        default=[],
        help=(
            "Optional points to track. "
            "Example: --track 3,1 7,3 14,8"
        ),
    )

    args = parser.parse_args()

    try:
        check_always_right_path(
            elements=args.elements,
            tracked_points=args.track,
        )
    except ValueError as error:
        print(error)
        sys.exit(1)


if __name__ == "__main__":
    main()