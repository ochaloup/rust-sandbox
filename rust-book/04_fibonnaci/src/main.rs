use std::io;

fn main() {
    println!("Enter unsigned number to get printed fibonnaci value");
    let mut sequence_number = String::new();
    io::stdin().read_line(&mut sequence_number).expect("Input reading error");
    let sequence_number: u32 = sequence_number.trim().parse().expect("Input is not a unsigned number");

    let mut result: u32 = 0;
    let mut next: u32 = 1;
    for _ in 1..sequence_number {
        let previous = result;
        result = next;
        next = previous + next;
    }
    println!("Fibonnaci number at place {} is: {}", sequence_number, result);
}
