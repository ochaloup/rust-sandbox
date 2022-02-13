use std::io;
use rand::Rng;
use std::cmp::Ordering;


fn main() {
    let max = 20;
    let rand_number = rand::thread_rng().gen_range(1..max);

    println!("Guess the number from 1 to {}!", max);
    
    loop {
        println!("Please input your guess.");

        let mut guess = String::new();

        io::stdin()
            .read_line(&mut guess)
            .expect("Failed to read line");

        if guess.trim().eq("quit") {
            break;
        }

        let guess: u32 = match guess.trim().parse() {
            Ok(number) => number,
            Err(_) => {
                println!("Input a number instead of '{}'", guess.trim());
                continue
            }
        };

        if guess > max {
            eprint!("Max permitted number was said to be {}!!!\n", max);
            break;
        }

        // println!("Your guess was {}", guess);
        match guess.cmp(&rand_number) {
            Ordering::Less => println!("Too small!"),
            Ordering::Greater => println!("Too big!"),
            Ordering::Equal => { 
                println!("You win! The secret number was {}", rand_number);
                break;
            }
        }
    }
}
