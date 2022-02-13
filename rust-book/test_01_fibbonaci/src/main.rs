use std::io;

fn main() {
    println!("Enter unsigned number to get printed fibonnaci value");
    let mut sequence_number = String::new();
    io::stdin().read_line(&mut sequence_number).expect("Input reading error");
    let sequence_number: u32 = sequence_number.trim().parse().expect("Input is not a unsigned number");

    let mut current: u64 = 0;
    let mut next: u64 = 1;
    for _ in 1..sequence_number {
        let previous = current;
        current = next;
        next = previous + current;
    }
    println!("Fibonnaci number at place {} is: {}", sequence_number, current);
}
