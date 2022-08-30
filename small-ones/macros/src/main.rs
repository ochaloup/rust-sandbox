
#[derive(Debug)]
struct OhMyStruct {
    name: String,
    age: u8,
}

impl OhMyStruct {
    pub fn new() -> Self {
        return OhMyStruct {
            name: String::from("Richard"),
            age: 42,
        }
    }
}

fn main() {

    println!("Hello, world! {:?}", OhMyStruct::new());
}
